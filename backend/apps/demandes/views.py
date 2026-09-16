"""
Endpoints des demandes.

Isolation des données : `get_queryset` restreint un distributeur à SES demandes. Une demande
d'un autre distributeur renvoie donc 404 (et non 403) : on ne révèle pas son existence.
Les contrôles d'état sont délégués aux services (409).
"""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import ConflitVersion
from apps.core.permissions import EstDistributeur

from .choices import Decision, Statut, TypeChantier, TypeIntervention, Usage
from .filters import DemandeFilter
from .models import Demande
from .serializers.demande import (
    DemandeDetailSerializer,
    DemandeListeSerializer,
    FDRPatchSerializer,
    HistoriqueSerializer,
)
from .serializers.fdr import FDRSerializer
from .services import workflow

ACTIONS_DISTRIBUTEUR = {"create", "destroy", "fdr"}


@extend_schema(tags=["demandes"])
class DemandeViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    filterset_class = DemandeFilter
    search_fields = ["reference", "fdr__assure_nom", "fdr__chantier_nom", "fdr__chantier_ville", "fdr__numero_contrat"]
    ordering_fields = ["created_at", "updated_at", "submitted_at", "reference", "statut"]
    ordering = ["-updated_at"]

    # ------------------------------------------------------------------ accès
    def get_permissions(self):  # type: ignore[override]
        if self.action in ACTIONS_DISTRIBUTEUR:
            return [IsAuthenticated(), EstDistributeur()]
        return [IsAuthenticated()]

    def get_queryset(self):  # type: ignore[override]
        qs = Demande.objects.select_related("fdr", "distributeur", "decided_by")
        utilisateur = self.request.user
        if utilisateur.est_siege:
            return qs
        return qs.filter(distributeur=utilisateur)

    def get_serializer_class(self):  # type: ignore[override]
        return DemandeListeSerializer if self.action == "list" else DemandeDetailSerializer

    # ------------------------------------------------------------------ CRUD
    @extend_schema(summary="Créer une demande (brouillon)", request=None, responses={201: DemandeDetailSerializer})
    def create(self, request: Request, *args, **kwargs) -> Response:
        demande = workflow.creer_demande(request.user)
        demande = self.get_queryset().get(pk=demande.pk)
        return Response(
            DemandeDetailSerializer(demande, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(summary="Supprimer un brouillon jamais envoyé")
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        demande = self.get_object()
        workflow.supprimer(demande.pk)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Liste des demandes (filtres statut / décision, recherche, tri)",
        parameters=[OpenApiParameter("search", str, description="Référence, assuré, chantier, contrat")],
    )
    def list(self, request: Request, *args, **kwargs) -> Response:
        return super().list(request, *args, **kwargs)

    # ------------------------------------------------------------------ FDR
    @extend_schema(
        summary="Lire / modifier le FDR (brouillon, verrou optimiste `version`)",
        request=FDRPatchSerializer,
        responses=DemandeDetailSerializer,
        methods=["PATCH"],
    )
    @extend_schema(summary="Lire le FDR", responses=FDRSerializer, methods=["GET"])
    @action(detail=True, methods=["get", "patch"], url_path="fdr")
    def fdr(self, request: Request, pk=None) -> Response:
        demande = self.get_object()
        if request.method == "GET":
            return Response(FDRSerializer(demande.fdr).data)

        if not demande.est_editable:
            from apps.core.exceptions import TransitionInvalide

            raise TransitionInvalide(
                "Le FDR n'est modifiable qu'en brouillon ou lorsque des compléments sont demandés.",
                statut_actuel=demande.statut,
            )
        version = request.data.get("version")
        if version is not None and int(version) != demande.version:
            raise ConflitVersion(version_actuelle=demande.version)

        serializer = FDRPatchSerializer(demande.fdr, data=request.data, partial=True, context={"mode": "brouillon"})
        serializer.is_valid(raise_exception=True)
        serializer.validated_data.pop("version", None)
        serializer.save()
        demande.version += 1
        demande.save(update_fields=["version", "updated_at"])
        demande = self.get_queryset().get(pk=demande.pk)
        return Response(DemandeDetailSerializer(demande, context=self.get_serializer_context()).data)

    # ------------------------------------------------------------------ sous-ressources
    @extend_schema(summary="Historique des actions", responses=HistoriqueSerializer(many=True))
    @action(detail=True, methods=["get"])
    def historique(self, request: Request, pk=None) -> Response:
        demande = self.get_object()
        return Response(HistoriqueSerializer(demande.historique.select_related("acteur"), many=True).data)


class ReferentielsView(APIView):
    """Valeurs de référence pour le formulaire dynamique du frontend."""

    @extend_schema(
        tags=["referentiels"],
        summary="Référentiels (choix du formulaire, seuils)",
        responses={200: OpenApiResponse(description="Référentiels")},
    )
    def get(self, request: Request) -> Response:
        from django.conf import settings

        def choix(enum) -> list[dict[str, str]]:
            return [{"code": c.value, "libelle": c.label} for c in enum]

        return Response(
            {
                "statuts": choix(Statut),
                "decisions": choix(Decision),
                "types_chantier": choix(TypeChantier),
                "usages": choix(Usage),
                "types_intervention": choix(TypeIntervention),
                "seuil_gros_chantier": settings.METIER["SEUIL_GROS_CHANTIER"],
            }
        )
