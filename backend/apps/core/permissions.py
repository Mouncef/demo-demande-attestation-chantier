"""
Permissions par rôle.

Les permissions ne vérifient QUE le rôle. Les contrôles liés à l'état de la demande vivent
dans les services (→ 409) et l'isolation des données dans `get_queryset` (→ 404).
"""

from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from apps.comptes.models import Role


class EstDistributeur(BasePermission):
    """Autorise uniquement les utilisateurs de rôle DISTRIBUTEUR (agent général / courtier)."""

    message = "Réservé aux distributeurs."

    def has_permission(self, request: Request, view) -> bool:  # type: ignore[override]
        return bool(request.user and request.user.is_authenticated and request.user.role == Role.DISTRIBUTEUR)


class EstSiege(BasePermission):
    """Autorise uniquement les utilisateurs de rôle SIEGE."""

    message = "Réservé au siège."

    def has_permission(self, request: Request, view) -> bool:  # type: ignore[override]
        return bool(request.user and request.user.is_authenticated and request.user.role == Role.SIEGE)
