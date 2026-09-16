"""
Endpoints des demandes.

Isolation des données : `get_queryset` restreint un distributeur à SES demandes. Une demande
d'un autre distributeur renvoie donc 404 (et non 403) : on ne révèle pas son existence.
Les contrôles d'état sont délégués aux services (409).
"""

from __future__ import annotations

from django.db.models import Prefetch
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import ConflitVersion
from apps.core.permissions import EstDistributeur, EstSiege
from apps.pieces.catalogue import CATALOGUE

from .choices import Decision, Statut, TypeChantier, TypeIntervention, Usage
from .filters import DemandeFilter
from .models import Demande
from .serializers.demande import (
    AccepterSerializer,
    CommentaireSerializer,
    ComplementsSerializer,
    DemandeDetailSerializer,
    DemandeListeSerializer,
    EnvoyerSerializer,
    FDRPatchSerializer,
    HistoriqueSerializer,
    RefuserSerializer,
    RelancerSerializer,
    RelanceSerializer,
    SoumissionSerializer,
)
from .serializers.fdr import FDRSerializer, valider_pour_envoi
from .services import relance as service_relance
from .services import workflow
from .services.exigences import calculer_completude
from .services.scoring import calculer_scoring

ACTIONS_DISTRIBUTEUR = {"create", "destroy", "fdr", "envoyer", "relancer"}
ACTIONS_SIEGE = {"demander_complements", "accepter", "refuser"}


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
        if self.action in ACTIONS_SIEGE:
            return [IsAuthenticated(), EstSiege()]
        return [IsAuthenticated()]

    def get_queryset(self):  # type: ignore[override]
        from apps.attestations.models import Attestation

        qs = Demande.objects.select_related("fdr", "distributeur", "decided_by").prefetch_related(
            Prefetch("attestations", queryset=Attestation.objects.only("id", "demande_id", "kind", "statut")),
        )
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

    # ------------------------------------------------------------------ calculs
    @extend_schema(summary="Pièces requises, complétude et validité du FDR")
    @action(detail=True, methods=["get"])
    def completude(self, request: Request, pk=None) -> Response:
        demande = self.get_object()
        completude = calculer_completude(demande.fdr, workflow.pieces_actives(demande))
        erreurs_fdr = valider_pour_envoi(demande.fdr)
        return Response(
            {
                **completude.to_dict(),
                "fdr_valide": not erreurs_fdr,
                "erreurs_fdr": erreurs_fdr,
                "pret_pour_envoi": completude.complet and not erreurs_fdr,
            }
        )

    @extend_schema(summary="Scoring de risque simulé (calcul à la volée)")
    @action(detail=True, methods=["get"])
    def scoring(self, request: Request, pk=None) -> Response:
        demande = self.get_object()
        return Response(calculer_scoring(demande.fdr, workflow.pieces_actives(demande)).to_dict())

    # ------------------------------------------------------------------ transitions
    def _reponse_detail(self, demande: Demande) -> Response:
        demande = self.get_queryset().get(pk=demande.pk)
        return Response(DemandeDetailSerializer(demande, context=self.get_serializer_context()).data)

    @extend_schema(
        summary="Envoyer / renvoyer la demande au siège", request=EnvoyerSerializer, responses=DemandeDetailSerializer
    )
    @action(detail=True, methods=["post"])
    def envoyer(self, request: Request, pk=None) -> Response:
        demande = self.get_object()
        serializer = EnvoyerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._reponse_detail(
            workflow.envoyer(demande.pk, request.user, serializer.validated_data.get("commentaire"))
        )

    @extend_schema(
        summary="Relancer le siège par email (délai minimal 24 h)",
        request=RelancerSerializer,
        responses=RelanceSerializer,
    )
    @action(detail=True, methods=["post"])
    def relancer(self, request: Request, pk=None) -> Response:
        demande = self.get_object()
        serializer = RelancerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        relance = service_relance.relancer(demande.pk, request.user, serializer.validated_data.get("message", ""))
        return Response(RelanceSerializer(relance).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Siège : demander des éléments complémentaires",
        request=ComplementsSerializer,
        responses=DemandeDetailSerializer,
    )
    @action(detail=True, methods=["post"], url_path="demander-complements")
    def demander_complements(self, request: Request, pk=None) -> Response:
        demande = self.get_object()
        serializer = ComplementsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._reponse_detail(
            workflow.demander_complements(demande.pk, request.user, serializer.validated_data["message"])
        )

    @extend_schema(summary="Siège : accepter la demande", request=AccepterSerializer, responses=DemandeDetailSerializer)
    @action(detail=True, methods=["post"])
    def accepter(self, request: Request, pk=None) -> Response:
        demande = self.get_object()
        serializer = AccepterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._reponse_detail(
            workflow.accepter(demande.pk, request.user, serializer.validated_data.get("commentaire", ""))
        )

    @extend_schema(
        summary="Siège : refuser la demande (motif obligatoire)",
        request=RefuserSerializer,
        responses=DemandeDetailSerializer,
    )
    @action(detail=True, methods=["post"])
    def refuser(self, request: Request, pk=None) -> Response:
        demande = self.get_object()
        serializer = RefuserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._reponse_detail(
            workflow.refuser(
                demande.pk,
                request.user,
                serializer.validated_data["motif"],
                serializer.validated_data.get("commentaire", ""),
            )
        )

    @extend_schema(
        summary="Commentaire (distributeur si éditable, siège si en cours)",
        request=CommentaireSerializer,
        responses=DemandeDetailSerializer,
    )
    @action(detail=True, methods=["patch"])
    def commentaire(self, request: Request, pk=None) -> Response:
        from apps.core.exceptions import TransitionInvalide

        demande = self.get_object()
        serializer = CommentaireSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if request.user.est_siege:
            if demande.statut != Statut.EN_COURS:
                raise TransitionInvalide(
                    "Le siège ne peut commenter qu'une demande en cours.", statut_actuel=demande.statut
                )
            demande.commentaire_siege = serializer.validated_data["commentaire"]
            demande.save(update_fields=["commentaire_siege", "updated_at"])
        else:
            if not demande.est_editable:
                raise TransitionInvalide(
                    "Le commentaire n'est modifiable qu'en brouillon.", statut_actuel=demande.statut
                )
            demande.commentaire_distributeur = serializer.validated_data["commentaire"]
            demande.save(update_fields=["commentaire_distributeur", "updated_at"])
        return self._reponse_detail(demande)

    # ------------------------------------------------------------------ sous-ressources
    @extend_schema(summary="Historique des actions", responses=HistoriqueSerializer(many=True))
    @action(detail=True, methods=["get"])
    def historique(self, request: Request, pk=None) -> Response:
        demande = self.get_object()
        return Response(HistoriqueSerializer(demande.historique.select_related("acteur"), many=True).data)

    @extend_schema(summary="Historique des relances", responses=RelanceSerializer(many=True))
    @action(detail=True, methods=["get"])
    def relances(self, request: Request, pk=None) -> Response:
        demande = self.get_object()
        return Response(RelanceSerializer(demande.relances.select_related("envoyee_par"), many=True).data)

    @extend_schema(summary="Soumissions successives (snapshots)", responses=SoumissionSerializer(many=True))
    @action(detail=True, methods=["get"])
    def soumissions(self, request: Request, pk=None) -> Response:
        demande = self.get_object()
        return Response(SoumissionSerializer(demande.soumissions.all(), many=True).data)

    @extend_schema(
        summary="PDF du FDR d'une soumission", responses={200: OpenApiResponse(description="application/pdf")}
    )
    @action(detail=True, methods=["get"], url_path=r"soumissions/(?P<numero>\d+)/pdf")
    def soumission_pdf(self, request: Request, pk=None, numero: str = "1") -> FileResponse:
        demande = self.get_object()
        soumission = get_object_or_404(demande.soumissions, numero=int(numero))
        reponse = FileResponse(
            soumission.pdf.open("rb"),
            content_type="application/pdf",
            as_attachment=True,
            filename=f"FDR-{demande.reference}-{soumission.numero}.pdf",
        )
        reponse["X-Content-Type-Options"] = "nosniff"
        return reponse


class ReferentielsView(APIView):
    """Valeurs de référence pour le formulaire dynamique du frontend."""

    @extend_schema(
        tags=["referentiels"],
        summary="Référentiels (choix, catalogue de pièces, seuils)",
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
                "types_pieces": [
                    {"code": d.code, "libelle": d.libelle, "description": d.description} for d in CATALOGUE
                ],
                "seuil_gros_chantier": settings.METIER["SEUIL_GROS_CHANTIER"],
                "relance_cooldown_hours": settings.METIER["RELANCE_COOLDOWN_HOURS"],
                "upload": {
                    "max_bytes": settings.METIER["UPLOAD_MAX_BYTES"],
                    "extensions": [".pdf", ".jpg", ".jpeg", ".png"]
                    + ([".docx", ".xlsx"] if settings.METIER["UPLOAD_ALLOW_OFFICE"] else []),
                },
            }
        )
