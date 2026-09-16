"""Endpoints d'authentification : login, refresh, logout (blacklist), profil."""

import contextlib

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.core.throttling import LoginThrottle

from .serializers import LoginSerializer, LogoutSerializer, UtilisateurSerializer


@extend_schema(tags=["auth"], summary="Connexion (email + mot de passe) → tokens JWT")
class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = [LoginThrottle]


@extend_schema(tags=["auth"], summary="Renouvellement de l'access token (rotation du refresh)")
class RefreshView(TokenRefreshView):
    pass


class LogoutView(APIView):
    """Révoque le refresh token (liste noire) ; l'access token expire naturellement (30 min)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["auth"],
        summary="Déconnexion (révocation du refresh token)",
        request=LogoutSerializer,
        responses={204: OpenApiResponse(description="Token révoqué")},
    )
    def post(self, request: Request) -> Response:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Token déjà expiré ou invalide : la déconnexion est de toute façon effective.
        with contextlib.suppress(TokenError):
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """Profil de l'utilisateur connecté."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["auth"], summary="Profil de l'utilisateur connecté", responses=UtilisateurSerializer)
    def get(self, request: Request) -> Response:
        return Response(UtilisateurSerializer(request.user).data)


__all__ = ["AllowAny", "LoginView", "LogoutView", "MeView", "RefreshView"]
