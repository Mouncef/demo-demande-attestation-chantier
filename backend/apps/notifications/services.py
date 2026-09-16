"""
Émission des notifications in-app et des emails.

`emettre()` est appelé par les services de workflow à l'intérieur d'une transaction : les
lignes de notification sont créées immédiatement (même transaction), l'email est envoyé après
commit (`transaction.on_commit`) et son échec est journalisé sans faire échouer l'action
métier – l'in-app fait foi.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from email.mime.image import MIMEImage
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string

from apps.comptes.models import Role, User
from apps.documents.logo import LOGO_AXA_PNG

from .models import Notification, TypeNotification

if TYPE_CHECKING:
    from apps.demandes.models import Demande

logger = logging.getLogger(__name__)


def destinataires_siege() -> list[User]:
    """Utilisateurs du siège actifs (destinataires des événements côté distributeur)."""
    return list(User.objects.filter(role=Role.SIEGE, is_active=True))


def emails_siege() -> list[str]:
    """Adresses email du siège : boîte fonctionnelle si configurée, sinon chaque utilisateur SIEGE."""
    boite = settings.METIER.get("SIEGE_MAILBOX")
    if boite:
        return [boite]
    return [u.email for u in destinataires_siege()]


def lien_demande(demande: Demande) -> str:
    """URL de la demande dans le frontend (emails)."""
    return f"{settings.FRONTEND_URL}/demandes/{demande.id}"


def _titre_et_message(type_: str, demande: Demande, complement: str) -> tuple[str, str]:
    ref = demande.reference
    assure = demande.fdr.assure_nom or "assuré non renseigné"
    textes = {
        TypeNotification.DEMANDE_ENVOYEE: (
            f"Nouvelle demande {ref}",
            f"Le distributeur {demande.distributeur.nom_affichage} a envoyé la demande {ref} ({assure}).",
        ),
        TypeNotification.DEMANDE_RENVOYEE: (
            f"Demande {ref} complétée",
            f"Le distributeur a renvoyé la demande {ref} ({assure}) après compléments.",
        ),
        TypeNotification.RELANCE: (
            f"Relance sur la demande {ref}",
            f"Le distributeur {demande.distributeur.nom_affichage} relance le siège sur la demande {ref}."
            + (f" Message : {complement}" if complement else ""),
        ),
        TypeNotification.COMPLEMENTS_DEMANDES: (
            f"Compléments demandés – {ref}",
            f"Le siège demande des éléments complémentaires sur la demande {ref} : {complement}",
        ),
        TypeNotification.DEMANDE_TRAITEE: (
            f"Demande {ref} traitée : {demande.get_decision_display() if demande.decision else ''}".strip(),
            f"La demande {ref} ({assure}) a été traitée par le siège."
            + (f" Motif : {complement}" if complement else ""),
        ),
    }
    return textes[type_]


def _envoyer_email(sujet: str, destinataires: list[str], contexte: dict) -> bool:
    if not destinataires:
        return False
    try:
        texte = render_to_string("emails/notification.txt", contexte)
        html = render_to_string("emails/notification.html", contexte)
        email = EmailMultiAlternatives(subject=sujet, body=texte, to=destinataires)
        email.attach_alternative(html, "text/html")
        # Logo AXA embarqué (référencé par `cid:logo-axa` dans le gabarit HTML).
        logo = MIMEImage(LOGO_AXA_PNG, _subtype="png")
        logo.add_header("Content-ID", "<logo-axa>")
        logo.add_header("Content-Disposition", "inline", filename="logo-axa.png")
        email.mixed_subtype = "related"
        email.attach(logo)
        email.send(fail_silently=False)
        return True
    except Exception as exc:  # noqa: BLE001 – l'email ne doit jamais faire échouer l'action métier
        logger.error("Échec d'envoi de l'email « %s » : %s", sujet, exc)
        return False


def emettre(
    type_: str,
    demande: Demande,
    destinataires: Iterable[User],
    complement: str = "",
    emails: list[str] | None = None,
    copie: list[str] | None = None,
) -> list[Notification]:
    """
    Crée une notification par destinataire et programme l'email correspondant après commit.

    :param emails: adresses email à notifier (par défaut celles des destinataires in-app) ;
    :param copie: adresses supplémentaires en copie (ex. le distributeur pour une relance).
    """
    titre, message = _titre_et_message(type_, demande, complement)
    destinataires = list(destinataires)
    notifications = Notification.objects.bulk_create(
        [
            Notification(
                destinataire=u,
                type=type_,
                demande=demande,
                titre=titre,
                message=message,
                payload={
                    "demande_id": str(demande.id),
                    "reference": demande.reference,
                    "statut": demande.statut,
                    "decision": demande.decision,
                },
            )
            for u in destinataires
        ]
    )

    adresses = list(dict.fromkeys((emails if emails is not None else [u.email for u in destinataires]) + (copie or [])))
    contexte = {
        "titre": titre,
        "message": message,
        "reference": demande.reference,
        "lien": lien_demande(demande),
        "assure": demande.fdr.assure_nom,
        "chantier": demande.fdr.chantier_nom,
    }
    sujet = f"[Attestations chantier] {titre}"
    transaction.on_commit(lambda: _envoyer_email(sujet, adresses, contexte))
    logger.info("Notification %s émise pour %s (%d destinataire(s))", type_, demande.reference, len(destinataires))
    return notifications
