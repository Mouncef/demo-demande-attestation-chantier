from rest_framework import serializers

from .catalogue import LIBELLES
from .models import PieceJointe, TypePiece


class PieceJointeSerializer(serializers.ModelSerializer):
    libelle_type = serializers.SerializerMethodField()
    deposee_par = serializers.CharField(source="deposee_par.nom_affichage", read_only=True)

    class Meta:
        model = PieceJointe
        fields = [
            "id",
            "type_piece",
            "libelle_type",
            "nom_fichier",
            "nom_original",
            "mime",
            "taille",
            "sha256",
            "deposee_par",
            "created_at",
        ]
        read_only_fields = fields

    def get_libelle_type(self, obj: PieceJointe) -> str:
        return LIBELLES.get(obj.type_piece_id, obj.type_piece_id)


class UploadPieceSerializer(serializers.Serializer):
    """Corps multipart de l'upload : le fichier et son type."""

    fichier = serializers.FileField()
    type_piece = serializers.PrimaryKeyRelatedField(queryset=TypePiece.objects.all())


class ModifierTypePieceSerializer(serializers.Serializer):
    type_piece = serializers.PrimaryKeyRelatedField(queryset=TypePiece.objects.all())
