"""
Cycle de vie des attestations : édition, soumission du projet, correction, validation, PDF, analyse.

Règles :
  * PROJET (distributeur) : préparé uniquement une fois la demande ACCEPTÉE ; « soumis » au siège
    (notification + email), repris par le distributeur tant que le siège ne l'a pas exploité, ou
    renvoyé « à corriger » par le siège avec un commentaire ; figé dès que la définitive est validée ;
  * DEFINITIVE (siège) : établie uniquement si la demande est TRAITÉE et ACCEPTÉE **et** que le
    distributeur a soumis son projet (elle en est la reprise rectifiée) ; validable seulement si la
    dernière analyse IA porte sur le contenu courant et est COHÉRENTE, ou avec forçage justifié ;
    validée = numérotée et immuable ; invisible pour le distributeur tant qu'elle n'est pas validée.
"""

from __future__ import annotations

import time
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.comptes.models import User
from apps.core.exceptions import ErreurMetier, TransitionInvalide
from apps.demandes.choices import ActionHistorique
from apps.demandes.models import CompteurReference, Demande, HistoriqueTransition
from apps.documents.pdf import rendre_pdf
from apps.notifications.models import TypeNotification
from apps.notifications.services import destinataires_siege, emails_siege, emettre

from ..models import AnalyseIA, Attestation, KindAttestation, StatutAttestation
from . import analyse_ia
from .gabarit import calculer_variables, corps_initial, document_complet, periode_contrat, rafraichir_chips
from .sanitize import sanitiser_html


def definitive_validee(demande: Demande) -> bool:
    """Vrai si l'attestation définitive de la demande est établie (validée)."""
    return demande.attestations.filter(kind=KindAttestation.DEFINITIVE, statut=StatutAttestation.VALIDEE).exists()


def projet_soumis(demande: Demande) -> Attestation | None:
    """Projet d'attestation soumis par le distributeur (base de l'attestation définitive), s'il existe."""
    return demande.attestations.filter(kind=KindAttestation.PROJET, statut=StatutAttestation.SOUMISE).first()


def definitive_possible(demande: Demande) -> bool:
    """Le siège peut établir la définitive : projet soumis, ou définitive déjà entamée sur un projet soumis."""
    return demande.est_acceptee and (
        projet_soumis(demande) is not None or demande.attestations.filter(kind=KindAttestation.DEFINITIVE).exists()
    )


def _verifier_droit_edition(demande: Demande, kind: str, utilisateur: User) -> None:
    """Contrôles d'état pour l'édition (le rôle est vérifié par les permissions DRF)."""
    if not demande.est_acceptee:
        raise TransitionInvalide(
            "Le projet d'attestation se prépare une fois la demande acceptée par le siège."
            if kind == KindAttestation.PROJET
            else "L'attestation définitive ne peut être établie que pour une demande acceptée.",
            statut_actuel=demande.statut,
            decision=demande.decision,
        )
    if kind == KindAttestation.PROJET and definitive_validee(demande):
        raise TransitionInvalide("L'attestation définitive est établie : le projet n'est plus modifiable.")
    if kind == KindAttestation.DEFINITIVE and not definitive_possible(demande):
        raise TransitionInvalide(
            "L'attestation définitive s'établit à partir du projet soumis par le distributeur : "
            "aucun projet n'a encore été soumis.",
            statut_actuel=demande.statut,
            decision=demande.decision,
        )


def gabarit(demande: Demande, kind: str, utilisateur: User) -> dict[str, Any]:
    """
    Contenu initial proposé à l'éditeur : gabarit AXA pour le projet ; pour la définitive, copie du projet
    soumis par le distributeur (409 tant qu'aucun projet n'est soumis).
    """
    if kind == KindAttestation.DEFINITIVE:
        _verifier_droit_edition(demande, kind, utilisateur)
    variables = calculer_variables(
        demande, kind, signataire=utilisateur if kind == KindAttestation.DEFINITIVE else None
    )
    projet = projet_soumis(demande)
    if kind == KindAttestation.DEFINITIVE and projet:
        html = rafraichir_chips(projet.contenu_html, variables)
        contenu_json = projet.contenu_json
        source = "PROJET"
    else:
        html, contenu_json, source = corps_initial(variables), None, "GABARIT"
    return {
        "contenu_html": html,
        "contenu_json": contenu_json,
        "variables": variables,
        "source": source,
        "projet_soumis_le": projet.soumise_le if projet else None,
    }


def enregistrer(demande: Demande, kind: str, utilisateur: User, contenu_html: str, contenu_json: Any) -> Attestation:
    """Crée ou met à jour l'attestation `kind` (409 si validée / état incompatible)."""
    _verifier_droit_edition(demande, kind, utilisateur)
    with transaction.atomic():
        attestation, _ = Attestation.objects.select_for_update().get_or_create(
            demande=demande,
            kind=kind,
            defaults={"contenu_html": "", "created_by": utilisateur},
        )
        if attestation.est_validee:
            raise TransitionInvalide(
                "Cette attestation est validée et ne peut plus être modifiée.", statut_attestation=attestation.statut
            )
        if attestation.est_soumise:
            raise TransitionInvalide(
                "Le projet a été soumis au siège : reprenez-le avant de le modifier.",
                statut_attestation=attestation.statut,
            )
        attestation.contenu_html = sanitiser_html(contenu_html)
        attestation.contenu_json = contenu_json
        attestation.variables_snapshot = calculer_variables(demande, kind, attestation)
        attestation.save()
    return attestation


def _contexte_rendu(demande: Demande, attestation: Attestation, corps_html: str | None) -> dict[str, Any]:
    """Contexte du gabarit : corps fourni (sanitisé) ou contenu enregistré, variables courantes."""
    variables = calculer_variables(demande, attestation.kind, attestation)
    corps = sanitiser_html(corps_html) if corps_html is not None else attestation.contenu_html
    return document_complet(demande, corps, variables)


def html_rendu(demande: Demande, attestation: Attestation, corps_html: str | None = None) -> str:
    """HTML complet (cadre AXA + corps) pour prévisualisation."""
    from django.template.loader import render_to_string

    return render_to_string("pdf/attestation.html", _contexte_rendu(demande, attestation, corps_html))


def generer_pdf(demande: Demande, attestation: Attestation, corps_html: str | None = None) -> bytes:
    """PDF du document : contenu enregistré, ou contenu fourni (aperçu identique à l'export)."""
    return rendre_pdf("pdf/attestation.html", _contexte_rendu(demande, attestation, corps_html))


def analyser(demande: Demande, attestation: Attestation, utilisateur: User) -> AnalyseIA:
    """Lance l'analyse de cohérence sur le contenu courant (chips rafraîchies) et la persiste."""
    delai = settings.METIER["IA_SIMULATED_DELAY_MS"]
    if delai:
        time.sleep(delai / 1000)  # latence artificielle pour une expérience crédible
    variables = calculer_variables(demande, attestation.kind, attestation)
    html = rafraichir_chips(attestation.contenu_html, variables)
    # Dates du gabarit légitimes hors FDR : période de validité du contrat (année civile de l'édition).
    reference = attestation.validated_at.date() if attestation.validated_at else timezone.now().date()
    resultat = analyse_ia.analyser(demande.fdr, html, attestation.kind, dates_tolerees=periode_contrat(reference))
    # L'empreinte porte sur le contenu STOCKÉ : elle sert à vérifier que la validation
    # définitive s'appuie sur une analyse du contenu courant.
    resultat.contenu_hash = analyse_ia.empreinte(attestation.contenu_html)
    return AnalyseIA.objects.create(
        attestation=attestation,
        statut=resultat.statut,
        score=resultat.score,
        contenu_hash=resultat.contenu_hash,
        resultat=resultat.to_dict(),
        created_by=utilisateur,
    )


def valider(
    demande: Demande, attestation: Attestation, utilisateur: User, forcer: bool = False, justification: str = ""
) -> Attestation:
    """Validation de l'attestation DÉFINITIVE par le siège : numéro, PDF final, notification au distributeur."""
    if attestation.kind != KindAttestation.PROJET:
        _verifier_droit_edition(demande, attestation.kind, utilisateur)
    else:
        raise TransitionInvalide("Un projet ne se valide pas : il se soumet au siège.")
    with transaction.atomic():
        attestation = Attestation.objects.select_for_update().get(pk=attestation.pk)
        if attestation.est_validee:
            raise TransitionInvalide("Cette attestation est déjà validée.", statut_attestation=attestation.statut)
        if not attestation.contenu_html.strip():
            raise ErreurMetier("Le contenu de l'attestation est vide.", code="ATTESTATION_VIDE")

        derniere = attestation.analyses.order_by("-created_at").first()
        analyse_valide = (
            derniere is not None
            and derniere.contenu_hash == analyse_ia.empreinte(attestation.contenu_html)
            and derniere.statut == AnalyseIA.Statut.COHERENT
        )
        if not analyse_valide:
            if not forcer:
                raise ErreurMetier(
                    "La validation nécessite une analyse de cohérence COHÉRENTE sur le contenu courant, "
                    "ou un forçage justifié.",
                    code="ANALYSE_INCOHERENTE",
                    analyse_presente=derniere is not None,
                    analyse_a_jour=bool(
                        derniere and derniere.contenu_hash == analyse_ia.empreinte(attestation.contenu_html)
                    ),
                )
            if len(justification.strip()) < 10:
                raise ErreurMetier(
                    "Le forçage doit être justifié (10 caractères minimum).", code="JUSTIFICATION_REQUISE"
                )
            attestation.justification_forcage = justification.strip()

        attestation.numero = CompteurReference.suivant("ATT")
        attestation.statut = StatutAttestation.VALIDEE
        attestation.validated_at = timezone.now()
        attestation.validated_by = utilisateur
        attestation.variables_snapshot = calculer_variables(demande, attestation.kind, attestation)
        attestation.save()
        attestation.pdf.save(
            f"{attestation.numero}-{demande.reference}.pdf", ContentFile(generer_pdf(demande, attestation)), save=True
        )
        HistoriqueTransition.objects.create(
            demande=demande,
            action=ActionHistorique.ATTESTATION_DEFINITIVE_VALIDEE,
            acteur=utilisateur,
            de_statut=demande.statut,
            vers_statut=demande.statut,
            commentaire=f"Attestation {attestation.numero}" + (f" – forçage : {justification}" if forcer else ""),
        )
        emettre(TypeNotification.ATTESTATION_DISPONIBLE, demande, [demande.distributeur])
    return attestation


def soumettre(demande: Demande, attestation: Attestation, utilisateur: User) -> Attestation:
    """
    Soumission du projet au siège par le distributeur.

    Depuis EN_EDITION ou A_CORRIGER → SOUMISE : PDF du projet (filigrane), historique, notification
    et email au siège pour qu'il valide ou rectifie le projet en établissant la définitive.
    """
    if attestation.kind != KindAttestation.PROJET:
        raise TransitionInvalide("Seul le projet d'attestation se soumet au siège.")
    _verifier_droit_edition(demande, attestation.kind, utilisateur)
    with transaction.atomic():
        attestation = Attestation.objects.select_for_update().get(pk=attestation.pk)
        if attestation.statut not in (StatutAttestation.EN_EDITION, StatutAttestation.A_CORRIGER):
            raise TransitionInvalide("Ce projet a déjà été soumis au siège.", statut_attestation=attestation.statut)
        if not attestation.contenu_html.strip():
            raise ErreurMetier("Le contenu du projet est vide.", code="ATTESTATION_VIDE")
        attestation.statut = StatutAttestation.SOUMISE
        attestation.soumise_le = timezone.now()
        attestation.commentaire_siege = ""
        attestation.variables_snapshot = calculer_variables(demande, attestation.kind, attestation)
        attestation.save()
        attestation.pdf.save(
            f"PROJET-{demande.reference}.pdf", ContentFile(generer_pdf(demande, attestation)), save=True
        )
        HistoriqueTransition.objects.create(
            demande=demande,
            action=ActionHistorique.ATTESTATION_PROJET_SOUMISE,
            acteur=utilisateur,
            de_statut=demande.statut,
            vers_statut=demande.statut,
        )
        emettre(TypeNotification.PROJET_ATTESTATION_SOUMIS, demande, destinataires_siege(), emails=emails_siege())
    return attestation


def demander_correction(demande: Demande, attestation: Attestation, utilisateur: User, commentaire: str) -> Attestation:
    """Le siège renvoie un projet soumis au distributeur avec un commentaire (SOUMISE → A_CORRIGER)."""
    if attestation.kind != KindAttestation.PROJET:
        raise TransitionInvalide("Seul un projet d'attestation peut être renvoyé pour correction.")
    if definitive_validee(demande):
        raise TransitionInvalide("L'attestation définitive est établie : le projet n'est plus en circuit.")
    with transaction.atomic():
        attestation = Attestation.objects.select_for_update().get(pk=attestation.pk)
        if not attestation.est_soumise:
            raise TransitionInvalide(
                "Seul un projet soumis peut être renvoyé pour correction.", statut_attestation=attestation.statut
            )
        attestation.statut = StatutAttestation.A_CORRIGER
        attestation.commentaire_siege = commentaire.strip()
        attestation.save(update_fields=["statut", "commentaire_siege", "updated_at"])
        HistoriqueTransition.objects.create(
            demande=demande,
            action=ActionHistorique.ATTESTATION_PROJET_A_CORRIGER,
            acteur=utilisateur,
            de_statut=demande.statut,
            vers_statut=demande.statut,
            commentaire=attestation.commentaire_siege,
        )
        emettre(
            TypeNotification.PROJET_ATTESTATION_A_CORRIGER,
            demande,
            [demande.distributeur],
            complement=attestation.commentaire_siege,
        )
    return attestation


def rouvrir(demande: Demande, attestation: Attestation, utilisateur: User) -> Attestation:
    """Le distributeur reprend un projet soumis (SOUMISE → EN_EDITION) tant que la définitive n'est pas établie."""
    if attestation.kind != KindAttestation.PROJET:
        raise TransitionInvalide("Une attestation définitive validée ne peut pas être rouverte.")
    _verifier_droit_edition(demande, attestation.kind, utilisateur)
    if not attestation.est_soumise:
        raise TransitionInvalide("Seul un projet soumis peut être repris.", statut_attestation=attestation.statut)
    attestation.statut = StatutAttestation.EN_EDITION
    attestation.soumise_le = None
    attestation.pdf.delete(save=False)
    attestation.save()
    HistoriqueTransition.objects.create(
        demande=demande,
        action=ActionHistorique.ATTESTATION_PROJET_ROUVERTE,
        acteur=utilisateur,
        de_statut=demande.statut,
        vers_statut=demande.statut,
    )
    return attestation
