from django.urls import path

from . import views

base = "demandes/<uuid:demande_pk>/attestations/<str:kind>/"
urlpatterns = [
    path(base, views.AttestationView.as_view(), name="attestation"),
    path(base + "gabarit/", views.GabaritView.as_view(), name="attestation-gabarit"),
    path(base + "previsualiser/", views.PrevisualiserView.as_view(), name="attestation-previsualiser"),
    path(base + "pdf/", views.PdfView.as_view(), name="attestation-pdf"),
    path(base + "valider/", views.ValiderView.as_view(), name="attestation-valider"),
    path(base + "soumettre/", views.SoumettreView.as_view(), name="attestation-soumettre"),
    path(base + "demander-correction/", views.DemanderCorrectionView.as_view(), name="attestation-demander-correction"),
    path(base + "rouvrir/", views.RouvrirView.as_view(), name="attestation-rouvrir"),
    path(base + "analyser/", views.AnalyserView.as_view(), name="attestation-analyser"),
    path(base + "analyses/", views.AnalysesView.as_view(), name="attestation-analyses"),
]
