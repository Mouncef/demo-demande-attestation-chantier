"""
Relance du siège par le distributeur.

Règle du sujet : « relancer par email une demande dans un délai de 24 h après la première
relance » → interprétée comme un délai minimal de 24 h entre deux relances (glissant).
Un délai initial après l'envoi est également paramétrable (0 par défaut).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.comptes.models import User
from apps.core.exceptions import RelanceTropTot, TransitionInvalide
from apps.notifications.models import TypeNotification
from apps.notifications.services import destinataires_siege, emails_siege, emettre

from ..choices import ActionHistorique, Statut
from ..models import Demande, HistoriqueTransition, Relance


def prochaine_relance_possible(demande: Demande) -> datetime | None:
    """Date à partir de laquelle une relance est autorisée (None si la demande n'est pas EN_COURS)."""
    if demande.statut != Statut.EN_COURS or demande.submitted_at is None:
        return None
    cooldown = timedelta(hours=settings.METIER["RELANCE_COOLDOWN_HOURS"])
    initial = timedelta(hours=settings.METIER["RELANCE_DELAI_INITIAL_HOURS"])
    candidats = [demande.submitted_at + initial]
    derniere = demande.relances.order_by("-created_at").first()
    if derniere and derniere.created_at >= demande.submitted_at:
        candidats.append(derniere.created_at + cooldown)
    return max(candidats)


def relancer(demande_id: Any, acteur: User, message: str = "") -> Relance:
    """Enregistre la relance, notifie le siège par email et in-app."""
    with transaction.atomic():
        demande = (
            Demande.objects.select_for_update(of=("self",)).select_related("fdr", "distributeur").get(pk=demande_id)
        )
        if demande.statut != Statut.EN_COURS:
            raise TransitionInvalide(
                "Seule une demande en cours d'instruction peut être relancée.", statut_actuel=demande.statut
            )
        prochaine = prochaine_relance_possible(demande)
        maintenant = timezone.now()
        if prochaine and maintenant < prochaine:
            attente = int((prochaine - maintenant).total_seconds())
            raise RelanceTropTot(
                "Une relance a déjà été envoyée : le délai minimal de "
                f"{settings.METIER['RELANCE_COOLDOWN_HOURS']} h n'est pas écoulé.",
                prochaine_relance_possible=prochaine.isoformat(),
                retry_after=attente,
            )
        adresses = emails_siege()
        relance = Relance.objects.create(
            demande=demande, envoyee_par=acteur, message=message, destinataires=adresses, email_ok=bool(adresses)
        )
        HistoriqueTransition.objects.create(
            demande=demande,
            action=ActionHistorique.RELANCE,
            acteur=acteur,
            de_statut=demande.statut,
            vers_statut=demande.statut,
            commentaire=message,
        )
        emettre(
            TypeNotification.RELANCE,
            demande,
            destinataires_siege(),
            complement=message,
            emails=adresses,
            copie=[acteur.email],
        )
    return relance
