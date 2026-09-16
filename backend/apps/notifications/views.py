"""Endpoints des notifications : liste (les siennes), compteur, marquage lu."""

from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


@extend_schema(tags=["notifications"])
class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    filterset_fields = ["lu", "type"]

    def get_queryset(self):  # type: ignore[override]
        # Isolation : un utilisateur ne voit que ses propres notifications.
        return Notification.objects.filter(destinataire=self.request.user).select_related("demande")

    @extend_schema(
        summary="Nombre de notifications non lues", responses={200: OpenApiResponse(description='{"count": n}')}
    )
    @action(detail=False, methods=["get"], url_path="non-lues/count")
    def non_lues(self, request: Request) -> Response:
        return Response({"count": self.get_queryset().filter(lu=False).count()})

    @extend_schema(summary="Marquer une notification comme lue", request=None, responses=NotificationSerializer)
    @action(detail=True, methods=["post"], url_path="lire")
    def lire(self, request: Request, pk=None) -> Response:
        notification = self.get_object()
        if not notification.lu:
            notification.lu = True
            notification.lu_le = timezone.now()
            notification.save(update_fields=["lu", "lu_le"])
        return Response(self.get_serializer(notification).data)

    @extend_schema(summary="Tout marquer comme lu", request=None, responses={204: None})
    @action(detail=False, methods=["post"], url_path="lire-toutes")
    def lire_toutes(self, request: Request) -> Response:
        self.get_queryset().filter(lu=False).update(lu=True, lu_le=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)
