from django.contrib import admin

from .models import AnalyseIA, Attestation


@admin.register(Attestation)
class AttestationAdmin(admin.ModelAdmin):
    list_display = ["demande", "kind", "statut", "numero", "validated_at", "validated_by"]
    list_filter = ["kind", "statut"]
    readonly_fields = ["variables_snapshot", "contenu_json"]


@admin.register(AnalyseIA)
class AnalyseIAAdmin(admin.ModelAdmin):
    list_display = ["attestation", "statut", "score", "created_by", "created_at"]
