"""
Routage racine.

Toutes les routes métier sont versionnées sous `/api/v1/`. La documentation OpenAPI est
exposée sur `/api/docs/` (Swagger UI) et `/api/schema/` (YAML/JSON).
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/auth/", include("apps.comptes.urls")),
    path("api/v1/", include("apps.demandes.urls")),
    path("api/v1/", include("apps.pieces.urls")),
]

admin.site.site_header = "Attestations de chantier – Administration"
admin.site.site_title = "Attestations de chantier"
