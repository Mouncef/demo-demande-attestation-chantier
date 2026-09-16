"""
Scoring de risque simulé.

Le score n'a pas vocation à être actuariellement juste : il propose des indicateurs lisibles
et additifs, chacun justifié par un facteur du FDR, pour orienter l'instruction. La grille est
documentée dans docs/REGLES_METIER.md.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from ..choices import NiveauRisque, TypeChantier, TypeIntervention, Usage
from .exigences import Niveau, calculer_completude

SEUIL_MODERE = 30
SEUIL_ELEVE = 65


@dataclass
class Indicateur:
    code: str
    libelle: str
    points: int
    detail: str


@dataclass
class Scoring:
    points: int
    score: int
    niveau: str
    indicateurs: list[Indicateur]
    planchers: list[str] = field(default_factory=list)
    synthese: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "points": self.points,
            "score": self.score,
            "niveau": self.niveau,
            "indicateurs": [i.__dict__ for i in self.indicateurs],
            "planchers": self.planchers,
            "synthese": self.synthese,
        }


def _dec(valeur: Any) -> Decimal | None:
    return None if valeur is None else Decimal(valeur)


def _indicateurs(fdr: Any, pieces: list[Any]) -> list[Indicateur]:  # noqa: C901 – grille volontairement explicite
    ind: list[Indicateur] = []
    cout = _dec(fdr.cout_total)
    prestation = _dec(fdr.montant_prestation)

    # --- Montant global du chantier ---
    if cout is not None:
        if cout > Decimal("10000000"):
            ind.append(Indicateur("MONTANT", "Coût total du chantier", 35, "Chantier de plus de 10 M€"))
        elif cout > Decimal("2000000"):
            ind.append(Indicateur("MONTANT", "Coût total du chantier", 20, "Chantier entre 2 M€ et 10 M€"))
        elif cout >= Decimal("500000"):
            ind.append(Indicateur("MONTANT", "Coût total du chantier", 10, "Chantier entre 500 k€ et 2 M€"))
        else:
            ind.append(Indicateur("MONTANT", "Coût total du chantier", 0, "Chantier de moins de 500 k€"))

    # --- Montant de la prestation ---
    if prestation is not None and prestation > Decimal("1000000"):
        ind.append(Indicateur("MONTANT_PRESTATION", "Montant de la prestation", 5, "Prestation supérieure à 1 M€"))
    if (
        fdr.type_intervention == TypeIntervention.SOUS_TRAITANT
        and cout
        and prestation
        and prestation >= cout * Decimal("0.8")
    ):
        ind.append(
            Indicateur(
                "PART_PRESTATION",
                "Part de la prestation",
                5,
                "Sous-traitant déclarant au moins 80 % du coût total : à vérifier",
            )
        )

    # --- Nature du chantier ---
    if fdr.type_chantier == TypeChantier.RENOVATION:
        if fdr.modification_structure:
            ind.append(
                Indicateur(
                    "RENOVATION_STRUCTURE",
                    "Rénovation avec modification de structure",
                    25,
                    "Intervention sur la structure d'un existant",
                )
            )
        else:
            ind.append(Indicateur("RENOVATION", "Rénovation", 5, "Rénovation sans modification de structure"))
    if fdr.chantier_atypique:
        ind.append(Indicateur("ATYPIQUE", "Chantier atypique", 20, "Chantier déclaré atypique"))
    if fdr.activite_couverte is False:
        ind.append(
            Indicateur("HORS_CONTRAT", "Activité hors contrat", 30, "Activité déclarée hors du périmètre du contrat")
        )
    if fdr.travaux_standards is False:
        ind.append(Indicateur("NON_STANDARD", "Travaux non standards", 15, "Procédés ou travaux non traditionnels"))
    if fdr.type_intervention == TypeIntervention.SOUS_TRAITANT:
        ind.append(Indicateur("SOUS_TRAITANCE", "Sous-traitance", 10, "Intervention en qualité de sous-traitant"))

    # --- Durée ---
    if fdr.date_debut and fdr.date_fin:
        mois = (fdr.date_fin - fdr.date_debut).days / 30.4
        if mois > 36:
            ind.append(Indicateur("DUREE", "Durée du chantier", 15, "Chantier de plus de 36 mois"))
        elif mois > 18:
            ind.append(Indicateur("DUREE", "Durée du chantier", 10, "Chantier de 18 à 36 mois"))
        elif mois > 6:
            ind.append(Indicateur("DUREE", "Durée du chantier", 5, "Chantier de 6 à 18 mois"))
        else:
            ind.append(Indicateur("DUREE", "Durée du chantier", 0, "Chantier de moins de 6 mois"))

    # --- Usage ---
    usages = {
        Usage.HABITATION: (5, "Habitation : exposition décennale fréquente"),
        Usage.BUREAU: (0, "Bureau : exposition standard"),
        Usage.COMMERCE: (5, "Commerce : contraintes ERP"),
        Usage.AUTRE: (10, "Usage indéterminé (industriel, agricole…)"),
    }
    if fdr.usage in usages:
        pts, detail = usages[fdr.usage]
        ind.append(Indicateur("USAGE", "Destination de l'ouvrage", pts, detail))

    # --- Complétude documentaire ---
    completude = calculer_completude(fdr, pieces)
    if completude.manquants:
        ind.append(
            Indicateur(
                "DOSSIER_INCOMPLET",
                "Dossier incomplet",
                10,
                f"{len(completude.manquants)} pièce(s) requise(s) manquante(s)",
            )
        )
    recommandees_manquantes = [e for e in completude.exigences if e.niveau == Niveau.RECOMMANDE and not e.satisfait]
    if recommandees_manquantes:
        ind.append(
            Indicateur(
                "PIECE_RECOMMANDEE",
                "Pièce recommandée absente",
                3,
                ", ".join(e.libelle for e in recommandees_manquantes),
            )
        )

    # --- Antécédents simulés (déterministes à partir du numéro de contrat) ---
    if fdr.numero_contrat:
        empreinte = hashlib.sha256(fdr.numero_contrat.encode()).hexdigest()
        nb_sinistres = int(empreinte[:2], 16) % 4
        points = {0: 0, 1: 5, 2: 10, 3: 20}[nb_sinistres]
        ind.append(
            Indicateur(
                "SINISTRALITE_SIMULEE",
                "Antécédents sinistres (donnée simulée)",
                points,
                f"{nb_sinistres} sinistre(s) sur les 5 dernières années (simulation)",
            )
        )
    return ind


def _niveau(points: int) -> str:
    if points >= SEUIL_ELEVE:
        return NiveauRisque.ELEVE
    if points >= SEUIL_MODERE:
        return NiveauRisque.MODERE
    return NiveauRisque.FAIBLE


def _synthese(niveau: str, score: int, indicateurs: list[Indicateur], planchers: list[str]) -> str:
    libelles = {NiveauRisque.FAIBLE: "FAIBLE", NiveauRisque.MODERE: "MODÉRÉ", NiveauRisque.ELEVE: "ÉLEVÉ"}
    principaux = sorted((i for i in indicateurs if i.points > 0), key=lambda i: -i.points)[:3]
    phrases = [f"Niveau de risque {libelles[niveau]} (score {score}/100)."]
    if principaux:
        facteurs = ", ".join(f"{i.detail[0].lower()}{i.detail[1:]} (+{i.points})" for i in principaux)
        phrases.append(f"Principaux facteurs : {facteurs}.")
    incomplet = next((i for i in indicateurs if i.code == "DOSSIER_INCOMPLET"), None)
    if incomplet:
        phrases.append(f"Le dossier est incomplet ({incomplet.detail}).")
    if planchers:
        phrases.append(" ".join(planchers))
    recommandations = {
        NiveauRisque.FAIBLE: "Recommandation : instruction standard possible.",
        NiveauRisque.MODERE: "Recommandation : vérification ciblée des points signalés avant décision.",
        NiveauRisque.ELEVE: (
            "Recommandation : analyse approfondie par le siège ; envisager une demande de compléments avant décision."
        ),
    }
    phrases.append(recommandations[niveau])
    return " ".join(phrases)


def calculer_scoring(fdr: Any, pieces: list[Any]) -> Scoring:
    """Calcule le score, le niveau (avec planchers métier) et la synthèse textuelle."""
    indicateurs = _indicateurs(fdr, pieces)
    points = sum(i.points for i in indicateurs)
    niveau = _niveau(points)
    codes = {i.code for i in indicateurs}
    planchers: list[str] = []

    # Planchers : certaines combinaisons imposent un niveau minimal quel que soit le total.
    if "HORS_CONTRAT" in codes and ("ATYPIQUE" in codes or "RENOVATION_STRUCTURE" in codes):
        if niveau != NiveauRisque.ELEVE:
            planchers.append(
                "Niveau porté à ÉLEVÉ : activité hors contrat combinée à un chantier atypique ou structurel."
            )
        niveau = NiveauRisque.ELEVE
    elif "HORS_CONTRAT" in codes and niveau == NiveauRisque.FAIBLE:
        planchers.append("Niveau porté à MODÉRÉ : activité hors contrat.")
        niveau = NiveauRisque.MODERE

    score = min(100, points)
    return Scoring(
        points=points,
        score=score,
        niveau=niveau,
        indicateurs=indicateurs,
        planchers=planchers,
        synthese=_synthese(niveau, score, indicateurs, planchers),
    )
