"""Classes de limitation de débit ciblées."""

from rest_framework.throttling import AnonRateThrottle


class LoginThrottle(AnonRateThrottle):
    """Limite les tentatives de connexion par adresse IP (anti force brute)."""

    scope = "login"
