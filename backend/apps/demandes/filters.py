"""Filtres de la liste des demandes."""

import django_filters

from .choices import Decision, Statut
from .models import Demande


class DemandeFilter(django_filters.FilterSet):
    statut = django_filters.MultipleChoiceFilter(choices=Statut.choices)
    decision = django_filters.MultipleChoiceFilter(choices=Decision.choices)
    distributeur = django_filters.NumberFilter(field_name="distributeur_id")
    cree_apres = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    cree_avant = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Demande
        fields = ["statut", "decision", "distributeur"]
