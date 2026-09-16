"""
Machine à états des demandes.

Chaque transition :
  1. verrouille la demande (`select_for_update`) pour sérialiser les actions concurrentes ;
  2. vérifie le statut source (sinon `TransitionInvalide` → 409) et les préconditions ;
  3. applique les effets (statut, décision, snapshots, PDF) ;
  4. journalise dans `HistoriqueTransition` ;
  5. émet notifications et emails (envoyés après commit).

Les rôles sont contrôlés en amont par les permissions DRF (403) ; ici on ne traite que l'état.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.comptes.models import User
from apps.core.exceptions import DossierIncomplet, TransitionInvalide
from apps.core.utils import format_date, format_montant
from apps.documents.logo import LOGO_AXA_DATA_URI
from apps.documents.pdf import rendre_pdf
from apps.notifications.models import TypeNotification
from apps.notifications.services import destinataires_siege, emails_siege, emettre

from ..choices import ActionHistorique, Decision, Statut
from ..models import Demande, HistoriqueTransition, SoumissionFDR
from ..serializers.fdr import FDRSerializer, valider_pour_envoi
from .exigences import calculer_completude
from .scoring import calculer_scoring

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


def pieces_actives(demande: Demande) -> list[Any]:
    return list(demande.pieces.actives().select_related("type_piece"))


def contexte_pdf_fdr(demande: Demande, scoring: dict[str, Any], completude: dict[str, Any]) -> dict[str, Any]:
    """Contexte du gabarit PDF du FDR."""
    fdr = demande.fdr
    return {
        "logo": LOGO_AXA_DATA_URI,
        "demande": demande,
        "fdr": fdr,
        "distributeur": demande.distributeur,
        "date_edition": format_date(timezone.now().date()),
        "date_debut": format_date(fdr.date_debut),
        "date_fin": format_date(fdr.date_fin),
        "cout_total": format_montant(fdr.cout_total),
        "montant_prestation": format_montant(fdr.montant_prestation),
        "scoring": scoring,
        "completude": completude,
    }


def envoyer(demande_id: Any, acteur: User, commentaire: str | None = None) -> Demande:
    """
    Envoi (ou renvoi) de la demande au siège.

    Préconditions : statut BROUILLON ou A_COMPLETER, FDR valide en mode envoi, dossier complet.
    Effets : statut EN_COURS, soumission horodatée avec PDF du FDR et snapshots, notifications.
    """
    with transaction.atomic():
        demande = _verrouiller(demande_id)
        _exiger_statut(demande, Statut.BROUILLON, Statut.A_COMPLETER)

        erreurs = valider_pour_envoi(demande.fdr)
        if erreurs:
            raise ValidationError(erreurs)

        pieces = pieces_actives(demande)
        completude = calculer_completude(demande.fdr, pieces)
        if not completude.complet:
            raise DossierIncomplet(
                manquants=completude.manquants,
                libelles=[e.libelle for e in completude.exigences if e.code in completude.manquants],
            )

        renvoi = demande.statut == Statut.A_COMPLETER
        scoring = calculer_scoring(demande.fdr, pieces).to_dict()
        maintenant = timezone.now()
        if commentaire is not None:
            demande.commentaire_distributeur = commentaire

        demande.statut = Statut.EN_COURS
        demande.submitted_at = maintenant
        demande.first_submitted_at = demande.first_submitted_at or maintenant
        demande.nb_soumissions += 1
        demande.scoring_snapshot = scoring
        demande.message_complements = ""
        demande.save()

        # PDF du FDR : généré de façon synchrone ; un échec annule toute la transaction.
        pdf = rendre_pdf("pdf/fdr.html", contexte_pdf_fdr(demande, scoring, completude.to_dict()))
        soumission = SoumissionFDR(
            demande=demande,
            numero=demande.nb_soumissions,
            fdr_snapshot=FDRSerializer(demande.fdr).data,
            pieces_snapshot=list(completude.to_dict()["exigences"]) + completude.pieces_hors_exigence,
            scoring_snapshot=scoring,
            commentaire_distributeur=demande.commentaire_distributeur,
        )
        soumission.pdf.save(f"FDR-{demande.reference}-{soumission.numero}.pdf", ContentFile(pdf), save=True)

        _journaliser(
            demande,
            ActionHistorique.RENVOI if renvoi else ActionHistorique.ENVOI,
            acteur,
            Statut.A_COMPLETER if renvoi else Statut.BROUILLON,
            Statut.EN_COURS,
            commentaire=demande.commentaire_distributeur,
        )
        emettre(
            TypeNotification.DEMANDE_RENVOYEE if renvoi else TypeNotification.DEMANDE_ENVOYEE,
            demande,
            destinataires_siege(),
            emails=emails_siege(),
        )
    logger.info("Demande %s envoyée (envoi n°%d)", demande.reference, demande.nb_soumissions)
    return demande


def demander_complements(demande_id: Any, acteur: User, message: str) -> Demande:
    """Le siège renvoie la demande au distributeur pour compléments (EN_COURS → A_COMPLETER)."""
    with transaction.atomic():
        demande = _verrouiller(demande_id)
        _exiger_statut(demande, Statut.EN_COURS)
        demande.statut = Statut.A_COMPLETER
        demande.message_complements = message
        demande.save(update_fields=["statut", "message_complements", "updated_at"])
        _journaliser(demande, ActionHistorique.COMPLEMENTS, acteur, Statut.EN_COURS, Statut.A_COMPLETER, message)
        emettre(TypeNotification.COMPLEMENTS_DEMANDES, demande, [demande.distributeur], complement=message)
    return demande


def _decider(demande_id: Any, acteur: User, decision: str, commentaire: str, motif: str = "") -> Demande:
    with transaction.atomic():
        demande = _verrouiller(demande_id)
        _exiger_statut(demande, Statut.EN_COURS)
        demande.statut = Statut.TRAITE
        demande.decision = decision
        demande.decided_at = timezone.now()
        demande.decided_by = acteur
        if commentaire:
            demande.commentaire_siege = commentaire
        demande.motif_refus = motif
        demande.save()
        action = ActionHistorique.ACCEPTATION if decision == Decision.ACCEPTEE else ActionHistorique.REFUS
        _journaliser(demande, action, acteur, Statut.EN_COURS, Statut.TRAITE, motif or commentaire, decision)
        emettre(TypeNotification.DEMANDE_TRAITEE, demande, [demande.distributeur], complement=motif)
    logger.info("Demande %s traitée : %s", demande.reference, decision)
    return demande


def accepter(demande_id: Any, acteur: User, commentaire: str = "") -> Demande:
    """Acceptation par le siège (EN_COURS → TRAITE / ACCEPTEE)."""
    return _decider(demande_id, acteur, Decision.ACCEPTEE, commentaire)


def refuser(demande_id: Any, acteur: User, motif: str, commentaire: str = "") -> Demande:
    """Refus motivé par le siège (EN_COURS → TRAITE / REFUSEE)."""
    return _decider(demande_id, acteur, Decision.REFUSEE, commentaire, motif=motif)


def supprimer(demande_id: Any) -> None:
    """Suppression d'un brouillon jamais envoyé (avec ses pièces et fichiers)."""
    with transaction.atomic():
        demande = _verrouiller(demande_id)
        if demande.statut != Statut.BROUILLON or demande.first_submitted_at is not None:
            raise TransitionInvalide(
                "Seul un brouillon jamais envoyé peut être supprimé.", statut_actuel=demande.statut
            )
        for piece in demande.pieces.all():
            piece.fichier.delete(save=False)
        demande.delete()


def actions_possibles(demande: Demande, utilisateur: User) -> list[str]:
    """
    Actions que l'utilisateur peut déclencher sur la demande dans son état actuel.

    Calculé côté serveur pour que le frontend affiche les boutons sans dupliquer les règles.
    """
    actions: list[str] = []
    if utilisateur.est_distributeur and demande.distributeur_id == utilisateur.id:
        if demande.est_editable:
            actions += ["modifier_fdr", "gerer_pieces", "envoyer"]
        if demande.statut == Statut.BROUILLON and demande.first_submitted_at is None:
            actions.append("supprimer")
        if demande.statut == Statut.EN_COURS:
            actions.append("relancer")
    if utilisateur.est_siege and demande.statut == Statut.EN_COURS:
        actions += ["accepter", "refuser", "demander_complements", "commenter"]
    return actions
