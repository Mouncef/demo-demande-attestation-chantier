"""
Analyse de cohérence FDR ↔ attestation (« IA » simulée).

Suite de contrôles déterministes sur le texte de l'attestation, chacun produisant une
incohérence typée (code, sévérité, champ, message, extrait à surligner). Le score de cohérence
est 100 moins les pénalités ; l'attestation est COHERENTE si aucune incohérence majeure et
score ≥ 80. L'interface (entrée : FDR + HTML, sortie : JSON structuré) est conçue pour être
remplacée par un vrai LLM sans changer le frontend.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from bs4 import BeautifulSoup
from django.utils import timezone

from apps.core.utils import normaliser
from apps.demandes.choices import TypeIntervention

from ..models import KindAttestation

MAJEURE, MOYENNE, MINEURE = "MAJEURE", "MOYENNE", "MINEURE"
PENALITES = {MAJEURE: 25, MOYENNE: 10, MINEURE: 3}
SEUIL_COHERENT = 80

REGEX_DATE = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b")
MOIS = {
    m: i + 1
    for i, m in enumerate(
        [
            "janvier",
            "fevrier",
            "mars",
            "avril",
            "mai",
            "juin",
            "juillet",
            "aout",
            "septembre",
            "octobre",
            "novembre",
            "decembre",
        ]
    )
}
REGEX_DATE_LETTRES = re.compile(
    r"\b(\d{1,2})(?:er)?\s+(janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[ée]cembre)\s+(\d{4})\b",
    re.IGNORECASE,
)
REGEX_MONTANT = re.compile(r"(\d{1,3}(?:[   ]\d{3})+|\d{4,})(?:,(\d{2}))?\s?€")
PLACEHOLDERS = ("{{", "}}", "[à compléter]", "[a completer]", "xxx", "___", "à compléter")
GARANTIES_HORS_PERIMETRE = (
    "dommages-ouvrage",
    "dommages ouvrage",
    "dommage ouvrage",
    "tous risques chantier",
    "trc",
    "protection juridique",
    "bris de machine",
    "garantie financiere d achevement",
)
STOP_WORDS = {
    "avec",
    "pour",
    "dans",
    "sans",
    "sous",
    "cette",
    "cela",
    "leur",
    "leurs",
    "entre",
    "toute",
    "toutes",
    "tous",
    "ainsi",
}


@dataclass
class Incoherence:
    code: str
    severite: str
    champ: str | None
    message: str
    attendu: str | None = None
    trouve: str | None = None
    extrait: str | None = None
    offset: int | None = None
    longueur: int | None = None


@dataclass
class ResultatAnalyse:
    statut: str
    score: int
    contenu_hash: str
    resume: str
    incoherences: list[Incoherence] = field(default_factory=list)
    controles_ok: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "incoherences": [asdict(i) for i in self.incoherences]}


def empreinte(html: str) -> str:
    return hashlib.sha256((html or "").encode()).hexdigest()


def texte_brut(html: str) -> str:
    return re.sub(r"[ \t]+", " ", BeautifulSoup(html or "", "html.parser").get_text(" ")).strip()


class Analyseur:
    """Exécute les contrôles ; chaque méthode `_ctrl_*` ajoute une incohérence ou un contrôle OK."""

    def __init__(self, fdr: Any, html: str, kind: str, dates_tolerees: Iterable[date] = ()) -> None:
        self.fdr = fdr
        self.kind = kind
        self.html = html or ""
        self.texte = texte_brut(self.html)
        self.norm = normaliser(self.texte)
        # Dates légitimes hors FDR (période de validité du contrat, date du courrier) fournies par le gabarit.
        self.dates_tolerees = set(dates_tolerees)
        # Le tableau de garanties du format officiel porte des montants contractuels (plafonds, franchise)
        # et des garanties « non accordées » : il est exclu des contrôles de montants et de garanties.
        soupe = BeautifulSoup(self.html, "html.parser")
        for tableau in soupe.select("table.garanties"):
            tableau.decompose()
        self.texte_hors_tableau = texte_brut(str(soupe))
        self.norm_hors_tableau = normaliser(self.texte_hors_tableau)
        # Montants portés par les zones dynamiques contractuelles (plafond du coût de construction…).
        self.montants_toleres = {
            self._montant(m)
            for chip in soupe.find_all("span", attrs={"data-variable": True})
            if chip.get("data-variable") not in ("cout_total", "montant_prestation")
            for m in REGEX_MONTANT.finditer(chip.get_text(" "))
        } - {None}
        self.incoherences: list[Incoherence] = []
        self.ok: list[str] = []

    @staticmethod
    def _montant(m: re.Match[str]) -> Decimal | None:
        try:
            return Decimal(re.sub(r"[ \u202f\u00a0]", "", m.group(1)) + ("." + m.group(2) if m.group(2) else ""))
        except InvalidOperation:
            return None

    # ------------------------------------------------------------------ utilitaires
    def _ajouter(self, code: str, severite: str, champ: str | None, message: str, **kw: Any) -> None:
        extrait = kw.get("extrait")
        if extrait and kw.get("offset") is None:
            pos = self.texte.find(extrait)
            if pos >= 0:
                kw["offset"], kw["longueur"] = pos, len(extrait)
        self.incoherences.append(Incoherence(code=code, severite=severite, champ=champ, message=message, **kw))

    def _contient(self, valeur: str | None) -> bool:
        return bool(valeur) and normaliser(valeur) in self.norm

    def _verifier_presence(self, code: str, severite: str, champ: str, valeur: str | None, libelle: str) -> None:
        if not valeur:
            return
        if self._contient(valeur):
            self.ok.append(code)
        else:
            self._ajouter(
                code, severite, champ, f"{libelle} « {valeur} » n'apparaît pas dans l'attestation.", attendu=valeur
            )

    # ------------------------------------------------------------------ contrôles
    def _ctrl_vide(self) -> bool:
        if len(self.texte) < 50:
            self._ajouter(
                "ATTESTATION_VIDE", MAJEURE, None, "L'attestation est vide ou trop courte pour être analysée."
            )
            return True
        self.ok.append("ATTESTATION_VIDE")
        return False

    def _ctrl_placeholders(self) -> None:
        trouves = [p for p in PLACEHOLDERS if p in self.texte.lower()]
        chips_vides = [
            chip.get("data-variable")
            for chip in BeautifulSoup(self.html, "html.parser").find_all("span", attrs={"data-variable": True})
            if not chip.get_text(strip=True)
        ]
        if trouves or chips_vides:
            for p in trouves:
                pos = self.texte.lower().find(p)
                self._ajouter(
                    "PLACEHOLDER_NON_REMPLI",
                    MAJEURE,
                    None,
                    f"Un espace réservé « {self.texte[pos : pos + len(p)]} » n'a pas été complété.",
                    extrait=self.texte[pos : pos + len(p)],
                    offset=pos,
                    longueur=len(p),
                )
            for cle in chips_vides:
                self._ajouter(
                    "PLACEHOLDER_NON_REMPLI",
                    MAJEURE,
                    cle,
                    f"La zone dynamique « {cle} » est vide : le FDR ne renseigne pas cette donnée.",
                )
        else:
            self.ok.append("PLACEHOLDER_NON_REMPLI")

    def _ctrl_identite(self) -> None:
        self._verifier_presence("ASSURE_ABSENT", MAJEURE, "assure_nom", self.fdr.assure_nom, "Le nom de l'assuré")
        self._verifier_presence(
            "CONTRAT_ABSENT", MAJEURE, "numero_contrat", self.fdr.numero_contrat, "Le numéro de contrat"
        )
        self._verifier_presence("CHANTIER_ABSENT", MOYENNE, "chantier_nom", self.fdr.chantier_nom, "Le nom du chantier")
        self._verifier_presence(
            "VILLE_CHANTIER_ABSENTE", MOYENNE, "chantier_ville", self.fdr.chantier_ville, "La ville du chantier"
        )
        self._verifier_presence(
            "VILLE_ASSURE_ABSENTE", MINEURE, "assure_ville", self.fdr.assure_ville, "La ville de l'assuré"
        )
        # SIRET : accepté avec ou sans espaces de groupement (833 207 194 00014).
        siret = getattr(self.fdr, "assure_siret", None)
        if siret:
            if siret in re.sub(r"\s", "", self.texte):
                self.ok.append("SIRET_ABSENT")
            else:
                self._ajouter(
                    "SIRET_ABSENT",
                    MOYENNE,
                    "assure_siret",
                    f"Le SIRET de l'assuré « {siret} » n'apparaît pas dans l'attestation.",
                    attendu=siret,
                )

        # Un autre numéro de contrat que celui du FDR dans une mention « contrat n° … » ?
        if self.fdr.numero_contrat:
            for m in re.finditer(r"contrat\s*n\s*°?\s*:?\s*([A-Z0-9]{6,20})", self.texte, re.IGNORECASE):
                trouve = m.group(1).upper()
                if trouve != self.fdr.numero_contrat:
                    self._ajouter(
                        "CONTRAT_DIFFERENT",
                        MAJEURE,
                        "numero_contrat",
                        f"Le numéro de contrat « {trouve} » diffère de celui du FDR (« {self.fdr.numero_contrat} »).",
                        attendu=self.fdr.numero_contrat,
                        trouve=trouve,
                        extrait=m.group(1),
                        offset=m.start(1),
                        longueur=len(m.group(1)),
                    )
                    break
            else:
                self.ok.append("CONTRAT_DIFFERENT")

    def _dates_detectees(self) -> list[tuple[date | None, str, int]]:
        resultats: list[tuple[date | None, str, int]] = []
        for m in REGEX_DATE.finditer(self.texte):
            j, mo, a = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            try:
                resultats.append((date(a, mo, j), m.group(0), m.start()))
            except ValueError:
                resultats.append((None, m.group(0), m.start()))
        for m in REGEX_DATE_LETTRES.finditer(self.texte):
            mois = MOIS.get(normaliser(m.group(2)))
            try:
                resultats.append((date(int(m.group(3)), mois or 0, int(m.group(1))), m.group(0), m.start()))
            except ValueError:
                resultats.append((None, m.group(0), m.start()))
        return resultats

    def _ctrl_dates(self) -> None:
        dates = self._dates_detectees()
        if not dates:
            self._ajouter(
                "DATES_ABSENTES",
                MOYENNE,
                "date_debut",
                "Aucune date (période du chantier) n'apparaît dans l'attestation.",
            )
            return
        aujourdhui = timezone.now().date()
        attendues = {self.fdr.date_debut, self.fdr.date_fin, aujourdhui, *self.dates_tolerees}
        hors_fdr_signalee = False
        for valeur, brut, pos in dates:
            if valeur is not None and valeur.year < 2000:
                # Références législatives du format officiel (loi du 19 décembre 1990, décret de 1991…).
                continue
            if valeur is None:
                self._ajouter(
                    "DATE_INVALIDE",
                    MOYENNE,
                    "date_debut",
                    f"La date « {brut} » est invalide.",
                    extrait=brut,
                    offset=pos,
                    longueur=len(brut),
                )
            elif valeur > aujourdhui and valeur not in attendues and valeur != self.fdr.date_fin:
                # Date future ni égale à la fin du chantier : probable date d'édition erronée ou période modifiée.
                if not hors_fdr_signalee:
                    self._ajouter(
                        "DATE_HORS_FDR",
                        MOYENNE,
                        "date_fin",
                        f"La date « {brut} » ne correspond à aucune date du FDR.",
                        extrait=brut,
                        offset=pos,
                        longueur=len(brut),
                        attendu=f"{self.fdr.date_debut} → {self.fdr.date_fin}",
                    )
                    hors_fdr_signalee = True
            elif valeur not in attendues and not hors_fdr_signalee:
                self._ajouter(
                    "DATE_HORS_FDR",
                    MOYENNE,
                    "date_debut",
                    f"La date « {brut} » ne correspond à aucune date du FDR.",
                    extrait=brut,
                    offset=pos,
                    longueur=len(brut),
                    attendu=f"{self.fdr.date_debut} → {self.fdr.date_fin}",
                )
                hors_fdr_signalee = True
        if not hors_fdr_signalee:
            self.ok.append("DATE_HORS_FDR")
        # Période « du X au Y » inversée
        for m in re.finditer(r"du\s+(\d{1,2}/\d{1,2}/\d{4})\s+au\s+(\d{1,2}/\d{1,2}/\d{4})", self.texte, re.IGNORECASE):
            try:
                d1 = date(*map(int, reversed(m.group(1).split("/"))))
                d2 = date(*map(int, reversed(m.group(2).split("/"))))
            except ValueError:
                continue
            if d2 < d1:
                self._ajouter(
                    "PERIODE_INCOHERENTE",
                    MAJEURE,
                    "date_fin",
                    "La période indiquée se termine avant de commencer.",
                    extrait=m.group(0),
                    offset=m.start(),
                    longueur=len(m.group(0)),
                )
        if (
            self.fdr.date_debut
            and self.fdr.date_fin
            and any(v in (self.fdr.date_debut, self.fdr.date_fin) for v, _, _ in dates)
        ):
            self.ok.append("DATES_ABSENTES")

    def _ctrl_travaux(self) -> None:
        description = self.fdr.description_travaux or ""
        mots = {m for m in normaliser(description).split() if len(m) >= 5 and m not in STOP_WORDS}
        if not mots:
            return
        presents = sum(1 for m in mots if m in self.norm)
        if presents / len(mots) < 0.4:
            self._ajouter(
                "TRAVAUX_ABSENTS",
                MOYENNE,
                "description_travaux",
                "La description des travaux du FDR n'est pas reprise dans l'attestation.",
                attendu=description[:120],
            )
        else:
            self.ok.append("TRAVAUX_ABSENTS")

    def _ctrl_montants(self) -> None:
        references = [Decimal(v) for v in (self.fdr.cout_total, self.fdr.montant_prestation) if v is not None]
        if not references:
            return
        for m in REGEX_MONTANT.finditer(self.texte_hors_tableau):
            brut = m.group(0)
            valeur = self._montant(m)
            if valeur is None or valeur in self.montants_toleres:
                continue
            if not any(abs(valeur - ref) <= ref * Decimal("0.01") for ref in references):
                self._ajouter(
                    "MONTANT_DIFFERENT",
                    MOYENNE,
                    "cout_total",
                    f"Le montant « {brut} » ne correspond ni au coût total ni au montant de la prestation déclarés.",
                    extrait=brut,
                    attendu=" / ".join(f"{r:,.2f} €".replace(",", " ").replace(".", ",") for r in references),
                )
                return
        self.ok.append("MONTANT_DIFFERENT")

    def _ctrl_garanties(self) -> None:
        for terme in GARANTIES_HORS_PERIMETRE:
            if re.search(r"\b" + re.escape(normaliser(terme)) + r"\b", self.norm_hors_tableau):
                m = re.search(re.escape(terme.split()[0]), self.texte, re.IGNORECASE)
                self._ajouter(
                    "GARANTIE_NON_DECLAREE",
                    MAJEURE,
                    None,
                    f"L'attestation mentionne une garantie hors périmètre : « {terme} ».",
                    extrait=m.group(0) if m else terme,
                )
                return
        self.ok.append("GARANTIE_NON_DECLAREE")

    def _ctrl_activite(self) -> None:
        if self.fdr.activite_couverte is False:
            positif = re.search(r"rel[eè]vent des activit[ée]s d[ée]clar[ée]es", self.texte, re.IGNORECASE)
            if positif:
                self._ajouter(
                    "ACTIVITE_HORS_CONTRAT",
                    MAJEURE,
                    "activite_couverte",
                    "Le FDR déclare une activité hors contrat, mais l'attestation présente les travaux comme couverts.",
                    extrait=positif.group(0),
                    offset=positif.start(),
                    longueur=len(positif.group(0)),
                )
                return
        self.ok.append("ACTIVITE_HORS_CONTRAT")

    def _ctrl_intervention(self) -> None:
        if self.fdr.type_intervention == TypeIntervention.SOUS_TRAITANT:
            m = re.search(r"en qualit[ée] d'entreprise principale|titulaire du march[ée]", self.texte, re.IGNORECASE)
            if m:
                self._ajouter(
                    "TYPE_INTERVENTION",
                    MOYENNE,
                    "type_intervention",
                    "Le FDR déclare une sous-traitance mais l'attestation présente l'assuré "
                    "comme entreprise principale.",
                    extrait=m.group(0),
                    offset=m.start(),
                    longueur=len(m.group(0)),
                )
                return
        self.ok.append("TYPE_INTERVENTION")

    def _ctrl_mentions(self) -> None:
        if "ne peut engager l assureur au dela" not in self.norm:
            self._ajouter(
                "MENTION_RESERVE_ABSENTE",
                MOYENNE,
                None,
                "La réserve « ne peut engager l'assureur au-delà des clauses et conditions du contrat » est absente.",
            )
        else:
            self.ok.append("MENTION_RESERVE_ABSENTE")
        if "decennale" not in self.norm:
            self._ajouter(
                "MENTION_DECENNALE_ABSENTE",
                MOYENNE,
                None,
                "La garantie décennale, objet de l'attestation, n'est pas mentionnée.",
            )
        else:
            self.ok.append("MENTION_DECENNALE_ABSENTE")
        if self.kind == KindAttestation.DEFINITIVE:
            m = re.search(r"\b(projet|provisoire)\b", self.texte, re.IGNORECASE)
            if m and "projet non signe" not in self.norm[max(0, m.start() - 5) : m.start() + 25]:
                self._ajouter(
                    "DEFINITIVE_MENTION_PROJET",
                    MAJEURE,
                    None,
                    "Une attestation définitive ne doit pas mentionner « projet » ou « provisoire ».",
                    extrait=m.group(0),
                    offset=m.start(),
                    longueur=len(m.group(0)),
                )
            else:
                self.ok.append("DEFINITIVE_MENTION_PROJET")

    # ------------------------------------------------------------------ exécution
    def analyser(self) -> ResultatAnalyse:
        if not self._ctrl_vide():
            self._ctrl_placeholders()
            self._ctrl_identite()
            self._ctrl_dates()
            self._ctrl_travaux()
            self._ctrl_montants()
            self._ctrl_garanties()
            self._ctrl_activite()
            self._ctrl_intervention()
            self._ctrl_mentions()

        penalite = sum(PENALITES[i.severite] for i in self.incoherences)
        score = max(0, 100 - penalite)
        majeures = sum(1 for i in self.incoherences if i.severite == MAJEURE)
        moyennes = sum(1 for i in self.incoherences if i.severite == MOYENNE)
        mineures = len(self.incoherences) - majeures - moyennes
        coherent = majeures == 0 and score >= SEUIL_COHERENT
        if self.incoherences:
            resume = (
                f"{len(self.incoherences)} incohérence(s) détectée(s) "
                f"({majeures} majeure(s), {moyennes} moyenne(s), {mineures} mineure(s))."
            )
        else:
            resume = "Aucune incohérence détectée entre le FDR et l'attestation."
        return ResultatAnalyse(
            statut="COHERENT" if coherent else "INCOHERENT",
            score=score,
            contenu_hash=empreinte(self.html),
            resume=resume,
            incoherences=self.incoherences,
            controles_ok=sorted(set(self.ok)),
        )


def analyser(fdr: Any, html: str, kind: str, dates_tolerees: Iterable[date] = ()) -> ResultatAnalyse:
    """Point d'entrée : analyse le HTML (chips déjà rafraîchies) contre le FDR."""
    return Analyseur(fdr, html, kind, dates_tolerees).analyser()
