"""Modèles des attestations et des analyses de cohérence."""

from django.conf import settings
from django.db import models

from apps.core.models import ModeleUUID


class KindAttestation(models.TextChoices):
    PROJET = "PROJET", "Projet d'attestation (distributeur)"
    DEFINITIVE = "DEFINITIVE", "Attestation définitive (siège)"


class StatutAttestation(models.TextChoices):
    """
    Statuts : le PROJET passe EN_EDITION → SOUMISE (au siège) → éventuellement A_CORRIGER (renvoyé par le
    siège) → SOUMISE… ; la DEFINITIVE passe EN_EDITION → VALIDEE (numérotée, immuable).
    """

    EN_EDITION = "EN_EDITION", "En cours d'édition"
    SOUMISE = "SOUMISE", "Soumise au siège"
    A_CORRIGER = "A_CORRIGER", "À corriger"
    VALIDEE = "VALIDEE", "Validée"


class Attestation(ModeleUUID):
    """
    Contenu éditable d'une attestation (corps HTML produit par l'éditeur riche).

    * `contenu_html` est sanitisé côté serveur avant stockage (liste blanche de balises) ;
    * `contenu_json` est le document TipTap, conservé pour rouvrir l'éditeur à l'identique ;
    * `variables_snapshot` fige les valeurs injectées (assuré, chantier, dates…) à la validation.
    """

    demande = models.ForeignKey("demandes.Demande", on_delete=models.CASCADE, related_name="attestations")
    kind = models.CharField("type", max_length=20, choices=KindAttestation.choices)
    statut = models.CharField(
        "statut", max_length=20, choices=StatutAttestation.choices, default=StatutAttestation.EN_EDITION
    )
    contenu_html = models.TextField("contenu HTML")
    contenu_json = models.JSONField("document éditeur", null=True, blank=True)
    variables_snapshot = models.JSONField("variables", default=dict)
    numero = models.CharField("numéro d'attestation", max_length=20, blank=True)
    pdf = models.FileField("PDF", upload_to="attestations/%Y/%m/", max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    validated_at = models.DateTimeField("validée le", null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    justification_forcage = models.TextField("justification du forçage", blank=True)
    # Circuit du projet : date de soumission au siège et commentaire du siège en cas de renvoi pour correction.
    soumise_le = models.DateTimeField("soumise au siège le", null=True, blank=True)
    commentaire_siege = models.TextField("commentaire du siège (demande de correction)", blank=True)

    class Meta:
        verbose_name = "attestation"
        verbose_name_plural = "attestations"
        unique_together = [("demande", "kind")]
        ordering = ["kind"]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} – {self.demande_id}"

    @property
    def est_validee(self) -> bool:
        return self.statut == StatutAttestation.VALIDEE

    @property
    def est_soumise(self) -> bool:
        return self.statut == StatutAttestation.SOUMISE


class AnalyseIA(ModeleUUID):
    """Résultat d'une analyse de cohérence FDR ↔ attestation (simulée, déterministe)."""

    class Statut(models.TextChoices):
        COHERENT = "COHERENT", "Cohérent"
        INCOHERENT = "INCOHERENT", "Incohérences détectées"

    attestation = models.ForeignKey(Attestation, on_delete=models.CASCADE, related_name="analyses")
    statut = models.CharField(max_length=20, choices=Statut.choices)
    score = models.PositiveSmallIntegerField("score de cohérence (%)")
    contenu_hash = models.CharField("empreinte du contenu analysé", max_length=64)
    resultat = models.JSONField("résultat détaillé")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")

    class Meta:
        verbose_name = "analyse IA"
        verbose_name_plural = "analyses IA"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Analyse {self.statut} ({self.score} %)"
