"""Classes de limitation de débit ciblées (login, uploads)."""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginThrottle(AnonRateThrottle):
    """Limite les tentatives de connexion par adresse IP (anti force brute)."""

    scope = "login"


class UploadThrottle(UserRateThrottle):
    scope = "uploads"
