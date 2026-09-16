"""
Machine à états des demandes.

Chaque transition :
  1. verrouille la demande (`select_for_update`) pour sérialiser les actions concurrentes ;
  2. vérifie le statut source (sinon `TransitionInvalide` → 409) et les préconditions ;
  3. applique les effets ;
  4. journalise dans `HistoriqueTransition`.

Les rôles sont contrôlés en amont par les permissions DRF (403) ; ici on ne traite que l'état.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

from apps.comptes.models import User
from apps.core.exceptions import TransitionInvalide

from ..choices import ActionHistorique, Statut
from ..models import Demande, HistoriqueTransition

logger = logging.getLogger(__name__)


def _verrouiller(demande_id: Any) -> Demande:
    """Recharge la demande avec un verrou de ligne (à appeler dans une transaction)."""
    # `of=("self",)` : verrouille uniquement la ligne de la demande
    # (les jointures nullables ne peuvent pas être verrouillées par PostgreSQL).
    return Demande.objects.select_for_update(of=("self",)).select_related("fdr", "distributeur").get(pk=demande_id)


def _exiger_statut(demande: Demande, *statuts: str) -> None:
    if demande.statut not in statuts:
        raise TransitionInvalide(
            f"Action impossible : la demande est au statut « {demande.get_statut_display()} ».",
            statut_actuel=demande.statut,
        )


def _journaliser(
    demande: Demande,
    action: str,
    acteur: User,
    de: str | None,
    vers: str | None,
    commentaire: str = "",
    decision: str | None = None,
) -> None:
    HistoriqueTransition.objects.create(
        demande=demande,
        action=action,
        acteur=acteur,
        de_statut=de,
        vers_statut=vers,
        commentaire=commentaire,
        decision=decision,
    )


def creer_demande(distributeur: User) -> Demande:
    """Crée une demande vide en BROUILLON avec son FDR."""
    from ..models import FDR  # import local pour éviter un cycle

    with transaction.atomic():
        demande = Demande.objects.create(distributeur=distributeur)
        FDR.objects.create(demande=demande)
        _journaliser(demande, ActionHistorique.CREATION, distributeur, None, Statut.BROUILLON)
    return demande


def supprimer(demande_id: Any) -> None:
    """Suppression d'un brouillon jamais envoyé."""
    with transaction.atomic():
        demande = _verrouiller(demande_id)
        if demande.statut != Statut.BROUILLON or demande.first_submitted_at is not None:
            raise TransitionInvalide(
                "Seul un brouillon jamais envoyé peut être supprimé.", statut_actuel=demande.statut
            )
        demande.delete()


def actions_possibles(demande: Demande, utilisateur: User) -> list[str]:
    """
    Actions que l'utilisateur peut déclencher sur la demande dans son état actuel.

    Calculé côté serveur pour que le frontend affiche les boutons sans dupliquer les règles.
    """
    actions: list[str] = []
    if utilisateur.est_distributeur and demande.distributeur_id == utilisateur.id:
        if demande.est_editable:
            actions.append("modifier_fdr")
        if demande.statut == Statut.BROUILLON and demande.first_submitted_at is None:
            actions.append("supprimer")
    return actions
