"""
Endpoints des pièces jointes d'une demande.

La demande parente est résolue via le queryset isolé (404 pour un distributeur non
propriétaire). Upload / modification / suppression sont réservés au distributeur propriétaire
lorsque la demande est éditable ; le téléchargement est ouvert au propriétaire et au siège.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.exceptions import ErreurMetier, TransitionInvalide
from apps.core.permissions import EstDistributeur
from apps.core.throttling import UploadThrottle
from apps.demandes.models import Demande

from .models import PieceJointe
from .serializers import ModifierTypePieceSerializer, PieceJointeSerializer, UploadPieceSerializer
from .services import nom_pour_type
from .validators import nettoyer_nom_original, valider_fichier


@extend_schema(tags=["pieces"])
class PieceViewSet(viewsets.GenericViewSet):
    serializer_class = PieceJointeSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = None

    def get_permissions(self):  # type: ignore[override]
        if self.action in {"create", "partial_update", "destroy"}:
            return [IsAuthenticated(), EstDistributeur()]
        return [IsAuthenticated()]

    def get_throttles(self):  # type: ignore[override]
        return [UploadThrottle()] if self.action == "create" else super().get_throttles()

    def _demande(self) -> Demande:
        qs = Demande.objects.select_related("fdr")
        if not self.request.user.est_siege:
            qs = qs.filter(distributeur=self.request.user)
        return get_object_or_404(qs, pk=self.kwargs["demande_pk"])

    def get_queryset(self):  # type: ignore[override]
        return PieceJointe.objects.actives().filter(demande=self._demande()).select_related("type_piece", "deposee_par")

    def _exiger_editable(self, demande: Demande) -> None:
        if not demande.est_editable:
            raise TransitionInvalide(
                "Les pièces ne sont modifiables qu'en brouillon ou lorsque des compléments sont demandés.",
                statut_actuel=demande.statut,
            )

    @extend_schema(summary="Liste des pièces de la demande", responses=PieceJointeSerializer(many=True))
    def list(self, request: Request, demande_pk=None) -> Response:
        return Response(self.get_serializer(self.get_queryset(), many=True).data)

    @extend_schema(
        summary="Déposer une pièce (multipart : fichier + type_piece)",
        request=UploadPieceSerializer,
        responses={201: PieceJointeSerializer},
    )
    def create(self, request: Request, demande_pk=None) -> Response:
        demande = self._demande()
        self._exiger_editable(demande)
        serializer = UploadPieceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fichier = serializer.validated_data["fichier"]
        type_piece = serializer.validated_data["type_piece"]

        valide = valider_fichier(fichier)

        with transaction.atomic():
            actives = PieceJointe.objects.actives().filter(demande=demande).select_for_update()
            if actives.count() >= settings.METIER["UPLOAD_MAX_PIECES_PAR_DEMANDE"]:
                raise ErreurMetier("Nombre maximal de pièces atteint pour cette demande.", code="QUOTA_PIECES")
            total = sum(p.taille for p in actives)
            if total + valide.taille > settings.METIER["UPLOAD_MAX_TOTAL_BYTES_PAR_DEMANDE"]:
                raise ErreurMetier("Volume total des pièces trop important pour cette demande.", code="QUOTA_PIECES")
            # Anti-doublon limité au même type : un même document peut légitimement servir à plusieurs
            # types de pièces (il est renommé d'après chaque type au dépôt).
            if actives.filter(sha256=valide.sha256, type_piece=type_piece).exists():
                raise ErreurMetier(
                    f"Ce fichier a déjà été déposé pour le type « {type_piece.libelle} ».", code="PIECE_DUPLIQUEE"
                )

            # La pièce est renommée d'après le libellé de son type (nom d'origine conservé pour information).
            nom_fichier = nom_pour_type(demande.pk, type_piece, valide.extension)
            piece = PieceJointe(
                demande=demande,
                type_piece=type_piece,
                nom_fichier=nom_fichier,
                nom_original=nettoyer_nom_original(fichier.name),
                mime=valide.mime,
                taille=valide.taille,
                sha256=valide.sha256,
                deposee_par=request.user,
            )
            # Le chemin de stockage est dérivé de `nom_fichier` (voir `chemin_piece`).
            piece.fichier.save(nom_fichier, fichier, save=True)
        return Response(PieceJointeSerializer(piece).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Changer le type d'une pièce", request=ModifierTypePieceSerializer, responses=PieceJointeSerializer
    )
    def partial_update(self, request: Request, demande_pk=None, pk=None) -> Response:
        demande = self._demande()
        self._exiger_editable(demande)
        piece = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = ModifierTypePieceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        nouveau_type = serializer.validated_data["type_piece"]
        if nouveau_type != piece.type_piece:
            # Le nom (affiché et stocké) suit le nouveau type : le fichier est déplacé sous son nouveau nom.
            piece.type_piece = nouveau_type
            piece.nom_fichier = nom_pour_type(demande.pk, nouveau_type, Path(piece.fichier.name).suffix, exclure=piece)
            ancien = piece.fichier.name
            with piece.fichier.open("rb") as contenu:
                piece.fichier.save(piece.nom_fichier, contenu, save=False)
            piece.fichier.storage.delete(ancien)
            piece.save(update_fields=["type_piece", "nom_fichier", "fichier", "updated_at"])
        return Response(PieceJointeSerializer(piece).data)

    @extend_schema(summary="Supprimer une pièce (suppression logique)")
    def destroy(self, request: Request, demande_pk=None, pk=None) -> Response:
        demande = self._demande()
        self._exiger_editable(demande)
        piece = get_object_or_404(self.get_queryset(), pk=pk)
        piece.deleted_at = timezone.now()
        piece.save(update_fields=["deleted_at", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Télécharger une pièce (authentifié, contrôle d'accès)",
        responses={200: OpenApiResponse(description="Flux binaire")},
    )
    @action(detail=True, methods=["get"])
    def download(self, request: Request, demande_pk=None, pk=None) -> FileResponse:
        piece = get_object_or_404(self.get_queryset(), pk=pk)
        # Défense en profondeur : le chemin vient de la base, on vérifie qu'il reste sous MEDIA_ROOT.
        chemin = Path(piece.fichier.path).resolve()
        if not chemin.is_relative_to(Path(settings.MEDIA_ROOT).resolve()) or not chemin.is_file():
            raise Http404
        reponse = FileResponse(
            chemin.open("rb"), content_type=piece.mime, as_attachment=True, filename=piece.nom_fichier
        )
        reponse["X-Content-Type-Options"] = "nosniff"
        return reponse
