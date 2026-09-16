from django.contrib import admin

from .models import FDR, Demande, HistoriqueTransition, Relance, SoumissionFDR


class FDRInline(admin.StackedInline):
    model = FDR
    can_delete = False


class HistoriqueInline(admin.TabularInline):
    model = HistoriqueTransition
    extra = 0
    readonly_fields = ["action", "de_statut", "vers_statut", "decision", "acteur", "commentaire", "created_at"]


@admin.register(Demande)
class DemandeAdmin(admin.ModelAdmin):
    list_display = ["reference", "statut", "decision", "distributeur", "submitted_at", "decided_at"]
    list_filter = ["statut", "decision"]
    search_fields = ["reference", "fdr__assure_nom", "fdr__chantier_nom"]
    readonly_fields = ["reference", "version", "scoring_snapshot", "created_at", "updated_at"]
    inlines = [FDRInline, HistoriqueInline]


admin.site.register(SoumissionFDR)
admin.site.register(Relance)
