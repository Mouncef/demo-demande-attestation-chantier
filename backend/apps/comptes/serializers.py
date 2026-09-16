"""Serializers d'authentification et de profil."""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User


class UtilisateurSerializer(serializers.ModelSerializer):
    """Profil de l'utilisateur connecté (lecture seule)."""

    nom_affichage = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "nom_affichage",
            "role",
            "organisation",
            "code_distributeur",
        ]
        read_only_fields = fields


class LoginSerializer(TokenObtainPairSerializer):
    """
    Login par email + mot de passe.

    Ajoute le rôle dans les claims du token (informatif côté front) et le profil dans la
    réponse pour éviter un second appel `GET /auth/me` après connexion.
    """

    @classmethod
    def get_token(cls, user):  # type: ignore[override]
        token = super().get_token(user)
        token["role"] = user.role
        token["email"] = user.email
        return token

    def validate(self, attrs):  # type: ignore[override]
        data = super().validate(attrs)
        data["utilisateur"] = UtilisateurSerializer(self.user).data
        return data


class LogoutSerializer(serializers.Serializer):
    """Corps de la déconnexion : le refresh token à révoquer."""

    refresh = serializers.CharField()
