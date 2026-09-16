"""Vues techniques (santé)."""

from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def health(request: HttpRequest) -> JsonResponse:
    """
    Sonde de santé pour Docker / Kubernetes.

    Vérifie l'accès à la base de données ; renvoie 503 en cas d'échec afin que
    l'orchestrateur retire l'instance du service.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:  # noqa: BLE001 – toute erreur = instance non saine
        return JsonResponse({"status": "ko", "database": "unreachable"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})
