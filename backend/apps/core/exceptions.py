"""
Exceptions métier et handler DRF.

Convention de codes HTTP (documentée dans docs/REGLES_METIER.md) :
  * 400 : données invalides (validation des serializers) ;
  * 401 : non authentifié / compte désactivé ;
  * 403 : rôle non autorisé pour l'action ;
  * 404 : ressource inexistante OU non visible par l'utilisateur (anti-énumération) ;
  * 409 : action refusée par l'état de la ressource (transition invalide, dossier incomplet…) ;
  * 413 / 415 : fichier trop volumineux / type non autorisé ;
  * 429 : trop de requêtes (relance trop tôt, throttling).

Toutes les erreurs sont renvoyées sous la forme `{"code": ..., "detail": ..., **extra}` afin
que le frontend puisse les traiter de façon homogène.
"""

from __future__ import annotations

import logging
from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException, Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class ErreurMetier(APIException):
    """Base des erreurs métier : porte un `code` machine et des données additionnelles."""

    status_code = status.HTTP_409_CONFLICT
    default_code = "ERREUR_METIER"
    default_detail = "Action impossible dans l'état actuel."

    def __init__(self, detail: str | None = None, code: str | None = None, **extra: Any) -> None:
        super().__init__(detail=detail or self.default_detail, code=code or self.default_code)
        self.code_metier = code or self.default_code
        self.extra = extra


class TransitionInvalide(ErreurMetier):
    """La transition de statut demandée n'est pas autorisée depuis l'état courant."""

    default_code = "TRANSITION_INVALIDE"
    default_detail = "Cette action n'est pas possible dans le statut actuel de la demande."


class DossierIncomplet(ErreurMetier):
    """Des pièces requises manquent : l'envoi au siège est bloqué."""

    default_code = "DOSSIER_INCOMPLET"
    default_detail = "Le dossier est incomplet : des pièces requises sont manquantes."


class ConflitVersion(ErreurMetier):
    """Verrou optimiste : la ressource a été modifiée entre-temps."""

    default_code = "CONFLIT_VERSION"
    default_detail = "La demande a été modifiée entre-temps. Rechargez la page avant de réessayer."


class RelanceTropTot(ErreurMetier):
    """Le délai minimal entre deux relances n'est pas écoulé."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "RELANCE_TROP_TOT"
    default_detail = "Une relance a déjà été envoyée récemment."


class FichierTropVolumineux(ErreurMetier):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_code = "FICHIER_TROP_VOLUMINEUX"
    default_detail = "Le fichier dépasse la taille maximale autorisée."


class TypeFichierNonAutorise(ErreurMetier):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    default_code = "TYPE_FICHIER_NON_AUTORISE"
    default_detail = "Ce type de fichier n'est pas autorisé."


def handler_exceptions(exc: Exception, context: dict[str, Any]) -> Response | None:
    """
    Handler DRF : normalise toutes les erreurs en `{"code", "detail", ...}`.

    Les erreurs de validation conservent leur détail par champ dans `errors` pour que le
    formulaire puisse surligner les champs concernés.
    """
    response = drf_exception_handler(exc, context)
    if response is None:
        # Exception non gérée : journalisée, réponse générique (pas de fuite d'information).
        logger.exception("Erreur non gérée dans %s", context.get("view"))
        return Response(
            {"code": "ERREUR_INTERNE", "detail": "Une erreur interne est survenue."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, ErreurMetier):
        payload: dict[str, Any] = {"code": exc.code_metier, "detail": str(exc.detail)}
        payload.update(exc.extra)
        response.data = payload
        if isinstance(exc, RelanceTropTot) and "retry_after" in exc.extra:
            response["Retry-After"] = str(exc.extra["retry_after"])
        return response

    if isinstance(exc, ValidationError):
        response.data = {
            "code": "VALIDATION",
            "detail": "Certaines données sont invalides.",
            "errors": response.data,
        }
        return response

    if isinstance(exc, Throttled):
        response.data = {"code": "TROP_DE_REQUETES", "detail": str(exc.detail)}
        return response

    # Autres APIException (401, 403, 404, 405…)
    code_map = {401: "NON_AUTHENTIFIE", 403: "INTERDIT", 404: "INTROUVABLE", 405: "METHODE_NON_AUTORISEE"}
    detail = response.data.get("detail", str(exc)) if isinstance(response.data, dict) else str(exc)
    response.data = {"code": code_map.get(response.status_code, "ERREUR"), "detail": str(detail)}
    return response
