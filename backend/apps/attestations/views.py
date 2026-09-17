"""
Endpoints des attestations : `/demandes/{id}/attestations/{kind}/…` avec kind ∈ {projet, definitive}.

Droits :
  * projet      : lecture propriétaire + siège ; écriture / soumission / reprise propriétaire ;
                  demande de correction par le siège ;
  * définitive  : écriture / analyse IA / validation siège ; le distributeur ne la voit (lecture, PDF)
                  qu'une fois validée.
"""

from __future__ import annotations

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.throttling import AnalyseIAThrottle
from apps.demandes.models import Demande

from .models import Attestation, KindAttestation
from .serializers import (
    AnalyseIASerializer,
    AttestationSerializer,
    DemanderCorrectionSerializer,
    EnregistrerAttestationSerializer,
    GabaritSerializer,
    PrevisualiserSerializer,
    ValiderAttestationSerializer,
)
from .services import cycle
from .services.gabarit import VARIABLES_DISPONIBLES, css_document, entete

KINDS = {"projet": KindAttestation.PROJET, "definitive": KindAttestation.DEFINITIVE}


class BaseAttestationView(APIView):
    permission_classes = [IsAuthenticated]

    def kind(self) -> str:
        try:
            return KINDS[self.kwargs["kind"]]
        except KeyError as exc:
            raise Http404 from exc

    def demande(self) -> Demande:
        qs = Demande.objects.select_related("fdr", "distributeur")
        if not self.request.user.est_siege:
            qs = qs.filter(distributeur=self.request.user)
        return get_object_or_404(qs, pk=self.kwargs["demande_pk"])

    def exiger_role_editeur(self, kind: str) -> None:
        """Le projet est édité par le distributeur, la définitive par le siège (sinon 403)."""
        utilisateur = self.request.user
        if kind == KindAttestation.PROJET and not utilisateur.est_distributeur:
            raise PermissionDenied("Le projet d'attestation est établi par le distributeur.")
        if kind == KindAttestation.DEFINITIVE and not utilisateur.est_siege:
            raise PermissionDenied("L'attestation définitive est établie par le siège.")

    def exiger_siege_definitive(self, kind: str) -> None:
        """L'analyse IA est réservée au siège, sur l'attestation définitive (sinon 403)."""
        if not self.request.user.est_siege:
            raise PermissionDenied("L'analyse de cohérence est réservée au siège.")
        if kind != KindAttestation.DEFINITIVE:
            raise PermissionDenied("L'analyse de cohérence porte sur l'attestation définitive.")

    def attestation(self, demande: Demande, kind: str) -> Attestation:
        attestation = get_object_or_404(
            Attestation.objects.select_related("validated_by", "created_by"), demande=demande, kind=kind
        )
        # Le distributeur ne voit l'attestation définitive qu'une fois établie (validée) par le siège.
        if kind == KindAttestation.DEFINITIVE and not self.request.user.est_siege and not attestation.est_validee:
            raise Http404
        return attestation


@extend_schema(tags=["attestations"])
class AttestationView(BaseAttestationView):
    @extend_schema(summary="Lire l'attestation (404 si elle n'existe pas encore)", responses=AttestationSerializer)
    def get(self, request: Request, demande_pk=None, kind=None) -> Response:
        demande = self.demande()
        return Response(
            AttestationSerializer(self.attestation(demande, self.kind()), context={"request": request}).data
        )

    @extend_schema(
        summary="Créer / mettre à jour le contenu",
        request=EnregistrerAttestationSerializer,
        responses=AttestationSerializer,
    )
    def put(self, request: Request, demande_pk=None, kind=None) -> Response:
        k = self.kind()
        self.exiger_role_editeur(k)
        demande = self.demande()
        serializer = EnregistrerAttestationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attestation = cycle.enregistrer(
            demande,
            k,
            request.user,
            serializer.validated_data["contenu_html"],
            serializer.validated_data.get("contenu_json"),
        )
        return Response(AttestationSerializer(attestation, context={"request": request}).data)


@extend_schema(tags=["attestations"])
class GabaritView(BaseAttestationView):
    @extend_schema(summary="Contenu initial (gabarit AXA ou copie du projet) et variables", responses=GabaritSerializer)
    def get(self, request: Request, demande_pk=None, kind=None) -> Response:
        k = self.kind()
        demande = self.demande()
        data = cycle.gabarit(demande, k, request.user)
        data["variables_disponibles"] = VARIABLES_DISPONIBLES
        # Identité de l'assureur : affichée dans l'en-tête non modifiable de l'éditeur (même cadre que le PDF).
        data["assureur"] = settings.METIER["ASSUREUR"]
        # Cadre du format officiel (intermédiaire, références, destinataire, date du courrier, mentions).
        data["entete"] = entete(data["variables"])
        # Feuille de style du document : l'éditeur l'applique pour un rendu identique au PDF.
        data["css_document"] = css_document()
        return Response(data)


@extend_schema(tags=["attestations"])
class PrevisualiserView(BaseAttestationView):
    @extend_schema(
        summary="Prévisualisation du contenu fourni ou enregistré : HTML (cadre AXA) ou PDF (`?sortie=pdf`)",
        request=PrevisualiserSerializer,
        parameters=[OpenApiParameter("sortie", str, description="`pdf` pour obtenir le PDF réel (défaut : HTML)")],
        responses={200: OpenApiResponse(description="text/html ou application/pdf")},
    )
    def post(self, request: Request, demande_pk=None, kind=None) -> HttpResponse:
        k = self.kind()
        demande = self.demande()
        serializer = PrevisualiserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attestation = Attestation.objects.filter(demande=demande, kind=k).first()
        if attestation is None:
            # Prévisualisation avant premier enregistrement : objet transitoire non persisté.
            attestation = Attestation(demande=demande, kind=k, contenu_html="", created_by=request.user)
        corps = serializer.validated_data.get("contenu_html")
        if request.query_params.get("sortie") == "pdf":
            # Aperçu = le PDF lui-même (même moteur et même gabarit que l'export) : rendu strictement identique.
            reponse = HttpResponse(cycle.generer_pdf(demande, attestation, corps), content_type="application/pdf")
            reponse["Content-Disposition"] = f'inline; filename="apercu-{demande.reference}.pdf"'
            reponse["X-Content-Type-Options"] = "nosniff"
            return reponse
        html = cycle.html_rendu(demande, attestation, corps)
        reponse = HttpResponse(html, content_type="text/html; charset=utf-8")
        reponse["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; img-src data:"
        reponse["X-Frame-Options"] = "SAMEORIGIN"
        return reponse


@extend_schema(tags=["attestations"])
class PdfView(BaseAttestationView):
    @extend_schema(
        summary="PDF de l'attestation (définitive : uniquement si validée)",
        responses={200: OpenApiResponse(description="application/pdf")},
    )
    def get(self, request: Request, demande_pk=None, kind=None) -> HttpResponse:
        k = self.kind()
        demande = self.demande()
        attestation = Attestation.objects.filter(demande=demande, kind=k).select_related("validated_by").first()
        if attestation is None:
            if k == KindAttestation.DEFINITIVE:
                raise Http404
            # Projet jamais enregistré : export « simulation » à partir du gabarit pré-rempli.
            attestation = Attestation(
                demande=demande,
                kind=k,
                contenu_html=cycle.gabarit(demande, k, request.user)["contenu_html"],
                created_by=request.user,
            )
        if k == KindAttestation.DEFINITIVE and not attestation.est_validee:
            raise Http404
        if attestation.pdf:
            reponse = FileResponse(
                attestation.pdf.open("rb"),
                content_type="application/pdf",
                as_attachment=True,
                filename=attestation.pdf.name.rsplit("/", 1)[-1],
            )
        else:
            # Projet en cours d'édition : PDF généré à la volée (simulation d'export).
            reponse = HttpResponse(cycle.generer_pdf(demande, attestation), content_type="application/pdf")
            reponse["Content-Disposition"] = f'attachment; filename="PROJET-{demande.reference}.pdf"'
        reponse["X-Content-Type-Options"] = "nosniff"
        return reponse


@extend_schema(tags=["attestations"])
class ValiderView(BaseAttestationView):
    @extend_schema(
        summary="Siège : valider l'attestation définitive (analyse cohérente requise ou forçage justifié)",
        request=ValiderAttestationSerializer,
        responses=AttestationSerializer,
    )
    def post(self, request: Request, demande_pk=None, kind=None) -> Response:
        k = self.kind()
        self.exiger_role_editeur(k)
        demande = self.demande()
        serializer = ValiderAttestationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attestation = cycle.valider(
            demande,
            self.attestation(demande, k),
            request.user,
            serializer.validated_data["forcer"],
            serializer.validated_data["justification"],
        )
        return Response(AttestationSerializer(attestation, context={"request": request}).data)


@extend_schema(tags=["attestations"])
class SoumettreView(BaseAttestationView):
    @extend_schema(
        summary="Soumettre le projet d'attestation au siège (notification + email)",
        request=None,
        responses=AttestationSerializer,
    )
    def post(self, request: Request, demande_pk=None, kind=None) -> Response:
        k = self.kind()
        self.exiger_role_editeur(k)
        demande = self.demande()
        attestation = cycle.soumettre(demande, self.attestation(demande, k), request.user)
        return Response(AttestationSerializer(attestation, context={"request": request}).data)


@extend_schema(tags=["attestations"])
class DemanderCorrectionView(BaseAttestationView):
    @extend_schema(
        summary="Siège : renvoyer le projet soumis au distributeur pour correction",
        request=DemanderCorrectionSerializer,
        responses=AttestationSerializer,
    )
    def post(self, request: Request, demande_pk=None, kind=None) -> Response:
        k = self.kind()
        if not request.user.est_siege:
            raise PermissionDenied("Seul le siège peut demander une correction du projet.")
        demande = self.demande()
        serializer = DemanderCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attestation = cycle.demander_correction(
            demande, self.attestation(demande, k), request.user, serializer.validated_data["commentaire"]
        )
        return Response(AttestationSerializer(attestation, context={"request": request}).data)


@extend_schema(tags=["attestations"])
class RouvrirView(BaseAttestationView):
    @extend_schema(summary="Reprendre un projet soumis (distributeur)", request=None, responses=AttestationSerializer)
    def post(self, request: Request, demande_pk=None, kind=None) -> Response:
        k = self.kind()
        self.exiger_role_editeur(k)
        demande = self.demande()
        attestation = cycle.rouvrir(demande, self.attestation(demande, k), request.user)
        return Response(AttestationSerializer(attestation, context={"request": request}).data)


@extend_schema(tags=["attestations"])
class AnalyserView(BaseAttestationView):
    """Analyse de cohérence : outil du siège pour établir l'attestation définitive (siège + définitive uniquement)."""

    throttle_classes = [AnalyseIAThrottle]

    @extend_schema(
        summary="Analyser la cohérence FDR ↔ attestation définitive (IA simulée, siège uniquement)",
        request=None,
        responses={201: AnalyseIASerializer},
    )
    def post(self, request: Request, demande_pk=None, kind=None) -> Response:
        k = self.kind()
        demande = self.demande()
        self.exiger_siege_definitive(k)
        analyse = cycle.analyser(demande, self.attestation(demande, k), request.user)
        return Response(AnalyseIASerializer(analyse).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["attestations"])
class AnalysesView(BaseAttestationView):
    @extend_schema(summary="Historique des analyses", responses=AnalyseIASerializer(many=True))
    def get(self, request: Request, demande_pk=None, kind=None) -> Response:
        k = self.kind()
        demande = self.demande()
        self.exiger_siege_definitive(k)
        attestation = self.attestation(demande, k)
        return Response(AnalyseIASerializer(attestation.analyses.select_related("created_by"), many=True).data)
