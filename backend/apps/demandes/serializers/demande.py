"""Serializers de la demande (liste, détail) et de ses sous-ressources."""

from __future__ import annotations

from rest_framework import serializers

from ..models import Demande, HistoriqueTransition
from ..services.workflow import actions_possibles
from .fdr import FDRSerializer


class DistributeurLegerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nom_affichage = serializers.CharField()
    email = serializers.EmailField()
    organisation = serializers.CharField()


class DemandeListeSerializer(serializers.ModelSerializer):
    """Ligne de la liste des demandes."""

    assure_nom = serializers.CharField(source="fdr.assure_nom", read_only=True)
    chantier_nom = serializers.CharField(source="fdr.chantier_nom", read_only=True)
    chantier_ville = serializers.CharField(source="fdr.chantier_ville", read_only=True)
    cout_total = serializers.DecimalField(
        source="fdr.cout_total", max_digits=14, decimal_places=2, read_only=True, coerce_to_string=True
    )
    distributeur = DistributeurLegerSerializer(read_only=True)
    niveau_risque = serializers.SerializerMethodField()
    actions_possibles = serializers.SerializerMethodField()

    class Meta:
        model = Demande
        fields = [
            "id",
            "reference",
            "statut",
            "decision",
            "distributeur",
            "assure_nom",
            "chantier_nom",
            "chantier_ville",
            "cout_total",
            "niveau_risque",
            "submitted_at",
            "decided_at",
            "nb_soumissions",
            "created_at",
            "updated_at",
            "actions_possibles",
        ]
        read_only_fields = fields

    def get_niveau_risque(self, obj: Demande) -> str | None:
        return (obj.scoring_snapshot or {}).get("niveau")

    def get_actions_possibles(self, obj: Demande) -> list[str]:
        return actions_possibles(obj, self.context["request"].user)


class DemandeDetailSerializer(DemandeListeSerializer):
    """Détail complet : FDR, commentaires, décision."""

    fdr = FDRSerializer(read_only=True)
    decided_by = DistributeurLegerSerializer(read_only=True)

    class Meta(DemandeListeSerializer.Meta):
        fields = DemandeListeSerializer.Meta.fields + [
            "fdr",
            "version",
            "commentaire_distributeur",
            "commentaire_siege",
            "motif_refus",
            "message_complements",
            "first_submitted_at",
            "decided_by",
            "scoring_snapshot",
        ]
        read_only_fields = fields


class HistoriqueSerializer(serializers.ModelSerializer):
    acteur = DistributeurLegerSerializer(read_only=True)
    action_libelle = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = HistoriqueTransition
        fields = [
            "id",
            "action",
            "action_libelle",
            "de_statut",
            "vers_statut",
            "decision",
            "acteur",
            "commentaire",
            "created_at",
        ]


class FDRPatchSerializer(FDRSerializer):
    """PATCH du FDR : ajoute le champ `version` (verrou optimiste) au corps."""

    version = serializers.IntegerField(required=False, min_value=1, write_only=True)
