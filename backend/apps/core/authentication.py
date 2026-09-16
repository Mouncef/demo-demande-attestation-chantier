"""Authentification JWT refusant les comptes désactivés même avec un token encore valide."""

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTAuthenticationActive(JWTAuthentication):
    """
    Variante de `JWTAuthentication` qui revérifie `is_active` à chaque requête.

    SimpleJWT vérifie déjà ce point à la lecture de l'utilisateur, mais on l'explicite ici
    pour que la désactivation d'un compte soit immédiatement effective (401) sans attendre
    l'expiration de l'access token.
    """

    def get_user(self, validated_token):  # type: ignore[override]
        user = super().get_user(validated_token)
        if not user.is_active:
            raise AuthenticationFailed("Compte désactivé.", code="user_inactive")
        return user
