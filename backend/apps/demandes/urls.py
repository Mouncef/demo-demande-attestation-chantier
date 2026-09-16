from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DemandeViewSet, ReferentielsView, ReportingView

router = DefaultRouter()
router.register("demandes", DemandeViewSet, basename="demandes")

urlpatterns = [
    path("referentiels/", ReferentielsView.as_view(), name="referentiels"),
    path("reporting/synthese/", ReportingView.as_view(), name="reporting-synthese"),
    *router.urls,
]
