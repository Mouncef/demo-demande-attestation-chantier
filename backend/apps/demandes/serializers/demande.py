"""Serializers de la demande (liste, détail) et de ses sous-ressources."""

from __future__ import annotations

from rest_framework import serializers

from ..models import Demande, HistoriqueTransition, Relance, SoumissionFDR
from ..services.relance import prochaine_relance_possible
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
    prochaine_relance_possible = serializers.SerializerMethodField()

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
            "prochaine_relance_possible",
        ]
        read_only_fields = fields

    def get_niveau_risque(self, obj: Demande) -> str | None:
        return (obj.scoring_snapshot or {}).get("niveau")

    def get_actions_possibles(self, obj: Demande) -> list[str]:
        return actions_possibles(obj, self.context["request"].user)

    def get_prochaine_relance_possible(self, obj: Demande) -> str | None:
        prochaine = prochaine_relance_possible(obj)
        return prochaine.isoformat() if prochaine else None


class DemandeDetailSerializer(DemandeListeSerializer):
    """Détail complet : FDR, commentaires, décision, compteurs de relance."""

    fdr = FDRSerializer(read_only=True)
    decided_by = DistributeurLegerSerializer(read_only=True)
    nb_relances = serializers.SerializerMethodField()
    derniere_relance_le = serializers.SerializerMethodField()

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
            "nb_relances",
            "derniere_relance_le",
        ]
        read_only_fields = fields

    def get_nb_relances(self, obj: Demande) -> int:
        return obj.relances.count()

    def get_derniere_relance_le(self, obj: Demande) -> str | None:
        derniere = obj.relances.order_by("-created_at").first()
        return derniere.created_at.isoformat() if derniere else None


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


class RelanceSerializer(serializers.ModelSerializer):
    envoyee_par = DistributeurLegerSerializer(read_only=True)

    class Meta:
        model = Relance
        fields = ["id", "message", "destinataires", "email_ok", "envoyee_par", "created_at"]


class SoumissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoumissionFDR
        fields = [
            "id",
            "numero",
            "fdr_snapshot",
            "pieces_snapshot",
            "scoring_snapshot",
            "commentaire_distributeur",
            "created_at",
        ]


# --- Corps des actions -------------------------------------------------------------------
class EnvoyerSerializer(serializers.Serializer):
    commentaire = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class RelancerSerializer(serializers.Serializer):
    message = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class ComplementsSerializer(serializers.Serializer):
    message = serializers.CharField(min_length=10, max_length=2000)


class AccepterSerializer(serializers.Serializer):
    commentaire = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class RefuserSerializer(serializers.Serializer):
    motif = serializers.CharField(min_length=10, max_length=2000)
    commentaire = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class CommentaireSerializer(serializers.Serializer):
    commentaire = serializers.CharField(allow_blank=True, max_length=2000)


class FDRPatchSerializer(FDRSerializer):
    """PATCH du FDR : ajoute le champ `version` (verrou optimiste) au corps."""

    version = serializers.IntegerField(required=False, min_value=1, write_only=True)
