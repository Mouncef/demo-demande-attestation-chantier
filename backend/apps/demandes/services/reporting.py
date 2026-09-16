"""
Indicateurs de reporting (globaux pour le siège, restreints pour un distributeur).

Tous les indicateurs sont calculés par agrégats SQL sur un même queryset filtré par la période
demandée, afin que toutes les vues de la page concordent.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q, QuerySet
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.attestations.models import Attestation, KindAttestation, StatutAttestation

from ..choices import Decision, NiveauRisque, Statut
from ..models import Demande

PERIODES_JOURS: dict[str, int | None] = {"30": 30, "90": 90, "365": 365, "tout": None}
NB_DISTRIBUTEURS_MAX = 6


def filtrer_periode(queryset: QuerySet[Demande], periode: str | None) -> tuple[QuerySet[Demande], str]:
    """Restreint aux demandes créées dans la période (`30`, `90`, `365` jours ou `tout`)."""
    cle = periode if periode in PERIODES_JOURS else "tout"
    jours = PERIODES_JOURS[cle]
    if jours:
        queryset = queryset.filter(created_at__gte=timezone.now() - timedelta(days=jours))
    return queryset, cle


def _moyenne_jours(queryset, champ_debut: str, champ_fin: str) -> float | None:
    """Délai moyen (jours, 1 décimale) entre deux horodatages non nuls."""
    delai = (
        queryset.filter(**{f"{champ_debut}__isnull": False, f"{champ_fin}__isnull": False})
        .annotate(d=ExpressionWrapper(F(champ_fin) - F(champ_debut), output_field=DurationField()))
        .aggregate(moyenne=Avg("d"))["moyenne"]
    )
    return round(delai.total_seconds() / 86400, 1) if delai else None


def _top_lignes(queryset: QuerySet[Demande], champs_nom: tuple[str, ...], en_instruction: Q) -> list[dict[str, Any]]:
    """Ventilation par entité (distributeur ou assuré) : les plus actifs, le reste plié dans « Autres »."""
    lignes = list(
        queryset.values(*champs_nom)
        .annotate(
            total=Count("id"),
            acceptees=Count("id", filter=Q(decision=Decision.ACCEPTEE)),
            refusees=Count("id", filter=Q(decision=Decision.REFUSEE)),
            en_instruction=Count("id", filter=en_instruction),
            brouillons=Count("id", filter=Q(statut=Statut.BROUILLON)),
        )
        .order_by("-total", *champs_nom)
    )
    principaux, autres = lignes[:NB_DISTRIBUTEURS_MAX], lignes[NB_DISTRIBUTEURS_MAX:]
    resultat = [
        {
            "nom": " ".join(str(ligne[c] or "") for c in champs_nom).strip() or "Non renseigné",
            "total": ligne["total"],
            "acceptees": ligne["acceptees"],
            "refusees": ligne["refusees"],
            "en_instruction": ligne["en_instruction"],
        }
        for ligne in principaux
    ]
    if autres:
        resultat.append(
            {
                "nom": f"Autres ({len(autres)})",
                **{
                    cle: sum(ligne[cle] for ligne in autres)
                    for cle in ("total", "acceptees", "refusees", "en_instruction")
                },
            }
        )
    return resultat


def synthese(
    queryset: QuerySet[Demande], periode: str | None = None, avec_distributeurs: bool = False
) -> dict[str, Any]:
    """
    Totaux, décisions, délais, volumes mensuels, niveaux de risque, circuit d'attestation et ventilation par
    entité : par distributeur pour le siège (`avec_distributeurs`), par assuré pour un distributeur.
    """
    queryset, periode_cle = filtrer_periode(queryset, periode)

    par_statut = dict(queryset.values_list("statut").annotate(n=Count("id")).values_list("statut", "n"))
    par_decision = dict(
        queryset.filter(decision__isnull=False)
        .values_list("decision")
        .annotate(n=Count("id"))
        .values_list("decision", "n")
    )
    total = queryset.count()
    traitees = par_statut.get(Statut.TRAITE, 0)
    acceptees = par_decision.get(Decision.ACCEPTEE, 0)
    refusees = par_decision.get(Decision.REFUSEE, 0)

    # --- Volumes mensuels (mois de création), ventilés par situation ---
    en_instruction = Q(statut__in=[Statut.EN_COURS, Statut.A_COMPLETER])
    par_mois = (
        queryset.annotate(mois=TruncMonth("created_at"))
        .values("mois")
        .annotate(
            total=Count("id"),
            acceptees=Count("id", filter=Q(decision=Decision.ACCEPTEE)),
            refusees=Count("id", filter=Q(decision=Decision.REFUSEE)),
            en_instruction=Count("id", filter=en_instruction),
            brouillons=Count("id", filter=Q(statut=Statut.BROUILLON)),
        )
        .order_by("mois")
    )

    # --- Niveaux de risque (scoring figé au dernier envoi) ---
    par_niveau = dict(
        queryset.filter(scoring_snapshot__niveau__isnull=False)
        .values_list("scoring_snapshot__niveau")
        .annotate(n=Count("id"))
        .values_list("scoring_snapshot__niveau", "n")
    )
    par_niveau_risque = {n.value: par_niveau.get(n.value, 0) for n in NiveauRisque}
    par_niveau_risque["NON_EVALUE"] = queryset.filter(scoring_snapshot__isnull=True).count()

    # --- Circuit d'attestation : acceptées → projets soumis → attestations établies ---
    ids = queryset.values("pk")
    projets_soumis = Attestation.objects.filter(
        demande__in=ids, kind=KindAttestation.PROJET, statut=StatutAttestation.SOUMISE
    ).count()
    attestations_etablies = Attestation.objects.filter(
        demande__in=ids, kind=KindAttestation.DEFINITIVE, statut=StatutAttestation.VALIDEE
    )
    projets_soumis_ou_exploites = (
        Attestation.objects.filter(demande__in=ids, kind=KindAttestation.PROJET)
        .filter(Q(statut=StatutAttestation.SOUMISE) | Q(demande__attestations__statut=StatutAttestation.VALIDEE))
        .distinct()
        .count()
    )
    circuit = {
        "acceptees": acceptees,
        "projets_soumis": max(projets_soumis, projets_soumis_ou_exploites),
        "attestations_etablies": attestations_etablies.count(),
    }

    # --- Délais ---
    delai_decision = _moyenne_jours(queryset, "first_submitted_at", "decided_at")
    delai_attestation = _moyenne_jours(
        attestations_etablies.annotate(decidee=F("demande__decided_at")), "decidee", "validated_at"
    )

    resultat: dict[str, Any] = {
        "periode": periode_cle,
        "total": total,
        "par_statut": {s.value: par_statut.get(s.value, 0) for s in Statut},
        "acceptees": acceptees,
        "refusees": refusees,
        "en_instruction": par_statut.get(Statut.EN_COURS, 0) + par_statut.get(Statut.A_COMPLETER, 0),
        "taux_acceptation": round(100 * acceptees / traitees, 1) if traitees else None,
        # Compatibilité : ancien nom conservé (= délai de décision)
        "delai_moyen_traitement_jours": delai_decision,
        "delai_moyen_decision_jours": delai_decision,
        "delai_moyen_attestation_jours": delai_attestation,
        "par_mois": [
            {
                "mois": ligne["mois"].strftime("%Y-%m"),
                "total": ligne["total"],
                "acceptees": ligne["acceptees"],
                "refusees": ligne["refusees"],
                "en_instruction": ligne["en_instruction"],
                "brouillons": ligne["brouillons"],
            }
            for ligne in par_mois
        ],
        "par_niveau_risque": par_niveau_risque,
        "circuit_attestation": circuit,
    }

    # --- Ventilation par entité et file « à traiter » selon le profil ---
    projets = Attestation.objects.filter(demande__in=ids, kind=KindAttestation.PROJET)
    if avec_distributeurs:
        # Siège : distributeurs les plus actifs ; à traiter = demandes en cours + projets soumis.
        resultat["par_distributeur"] = _top_lignes(
            queryset, ("distributeur__first_name", "distributeur__last_name"), en_instruction
        )
        resultat["a_traiter"] = (
            par_statut.get(Statut.EN_COURS, 0) + projets.filter(statut=StatutAttestation.SOUMISE).count()
        )
    else:
        # Distributeur : assurés les plus fréquents ; à traiter = compléments demandés + projets à corriger.
        resultat["par_assure"] = _top_lignes(queryset, ("fdr__assure_nom",), en_instruction)
        resultat["a_traiter"] = (
            par_statut.get(Statut.A_COMPLETER, 0) + projets.filter(statut=StatutAttestation.A_CORRIGER).count()
        )
    return resultat
