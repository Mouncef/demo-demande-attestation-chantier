from django.contrib import admin

from .models import PieceJointe, TypePiece


@admin.register(TypePiece)
class TypePieceAdmin(admin.ModelAdmin):
    list_display = ["code", "libelle", "ordre"]


@admin.register(PieceJointe)
class PieceJointeAdmin(admin.ModelAdmin):
    list_display = ["nom_original", "demande", "type_piece", "mime", "taille", "deleted_at"]
    list_filter = ["type_piece"]
    readonly_fields = ["sha256", "mime", "taille"]
