from rest_framework.routers import DefaultRouter

from .views import PieceViewSet

router = DefaultRouter()
router.register(r"demandes/(?P<demande_pk>[0-9a-f-]{36})/pieces", PieceViewSet, basename="pieces")
urlpatterns = router.urls
