from rest_framework import serializers

from .models import AnalyseIA, Attestation


class AttestationSerializer(serializers.ModelSerializer):
    validated_by = serializers.CharField(source="validated_by.nom_affichage", read_only=True, default=None)
    created_by = serializers.CharField(source="created_by.nom_affichage", read_only=True)
    pdf_disponible = serializers.SerializerMethodField()
    derniere_analyse = serializers.SerializerMethodField()
    analyse_a_jour = serializers.SerializerMethodField()

    class Meta:
        model = Attestation
        fields = [
            "id",
            "kind",
            "statut",
            "contenu_html",
            "contenu_json",
            "variables_snapshot",
            "numero",
            "pdf_disponible",
            "created_by",
            "validated_at",
            "validated_by",
            "justification_forcage",
            "derniere_analyse",
            "analyse_a_jour",
            "soumise_le",
            "commentaire_siege",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_pdf_disponible(self, obj: Attestation) -> bool:
        return bool(obj.pdf)

    def get_derniere_analyse(self, obj: Attestation) -> dict | None:
        """Résultat de la dernière analyse : réservé au siège (outil d'instruction)."""
        request = self.context.get("request")
        if request is not None and not request.user.est_siege:
            return None
        analyse = obj.analyses.order_by("-created_at").first()
        return AnalyseIASerializer(analyse).data if analyse else None

    def get_analyse_a_jour(self, obj: Attestation) -> bool:
        """Vrai si la dernière analyse porte sur le contenu actuellement enregistré."""
        from .services.analyse_ia import empreinte

        analyse = obj.analyses.order_by("-created_at").first()
        return bool(analyse and analyse.contenu_hash == empreinte(obj.contenu_html))


class EnregistrerAttestationSerializer(serializers.Serializer):
    contenu_html = serializers.CharField(allow_blank=True, max_length=200_000)
    contenu_json = serializers.JSONField(required=False, allow_null=True)


class PrevisualiserSerializer(serializers.Serializer):
    contenu_html = serializers.CharField(required=False, allow_blank=True, max_length=200_000)


class ValiderAttestationSerializer(serializers.Serializer):
    forcer = serializers.BooleanField(required=False, default=False)
    justification = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")


class DemanderCorrectionSerializer(serializers.Serializer):
    commentaire = serializers.CharField(min_length=10, max_length=2000)


class AnalyseIASerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.nom_affichage", read_only=True)

    class Meta:
        model = AnalyseIA
        fields = ["id", "statut", "score", "contenu_hash", "resultat", "created_by", "created_at"]
        read_only_fields = fields


class GabaritSerializer(serializers.Serializer):
    contenu_html = serializers.CharField()
    contenu_json = serializers.JSONField(allow_null=True)
    variables = serializers.DictField()
    source = serializers.CharField()
    projet_soumis_le = serializers.DateTimeField(allow_null=True)
    assureur = serializers.DictField(child=serializers.CharField())
    # Cadre du format officiel AXA : intermédiaire, références, destinataire, date du courrier, mentions légales.
    entete = serializers.DictField()
    # Feuille de style du document, appliquée par l'éditeur pour un rendu identique au PDF.
    css_document = serializers.CharField()
