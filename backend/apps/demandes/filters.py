"""Filtres de la liste des demandes."""

import django_filters

from .choices import Decision, Statut
from .models import Demande


class DemandeFilter(django_filters.FilterSet):
    statut = django_filters.MultipleChoiceFilter(choices=Statut.choices)
    decision = django_filters.MultipleChoiceFilter(choices=Decision.choices)
    distributeur = django_filters.NumberFilter(field_name="distributeur_id")
    # Projets d'attestation soumis en attente du siège (`?projet_soumis=true`).
    projet_soumis = django_filters.BooleanFilter(method="filtrer_projet_soumis")
    cree_apres = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    cree_avant = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Demande
        fields = ["statut", "decision", "distributeur"]

    def filtrer_projet_soumis(self, queryset, name, value):
        """Demandes dont le projet d'attestation est soumis au siège (et définitive non établie)."""
        soumis = queryset.filter(attestations__kind="PROJET", attestations__statut="SOUMISE").exclude(
            attestations__kind="DEFINITIVE", attestations__statut="VALIDEE"
        )
        return soumis.distinct() if value else queryset.exclude(pk__in=soumis.values("pk"))
