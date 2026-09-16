"""Modèle de notification in-app (une ligne par destinataire)."""

from django.conf import settings
from django.db import models

from apps.core.models import ModeleUUID


class TypeNotification(models.TextChoices):
    DEMANDE_ENVOYEE = "DEMANDE_ENVOYEE", "Demande envoyée"
    DEMANDE_RENVOYEE = "DEMANDE_RENVOYEE", "Demande renvoyée après compléments"
    RELANCE = "RELANCE", "Relance"
    COMPLEMENTS_DEMANDES = "COMPLEMENTS_DEMANDES", "Compléments demandés"
    DEMANDE_TRAITEE = "DEMANDE_TRAITEE", "Demande traitée"
    PROJET_ATTESTATION_SOUMIS = "PROJET_ATTESTATION_SOUMIS", "Projet d'attestation soumis"
    PROJET_ATTESTATION_A_CORRIGER = "PROJET_ATTESTATION_A_CORRIGER", "Projet d'attestation à corriger"
    ATTESTATION_DISPONIBLE = "ATTESTATION_DISPONIBLE", "Attestation disponible"


class Notification(ModeleUUID):
    destinataire = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField("type", max_length=40, choices=TypeNotification.choices)
    demande = models.ForeignKey(
        "demandes.Demande", on_delete=models.CASCADE, null=True, blank=True, related_name="notifications"
    )
    titre = models.CharField("titre", max_length=200)
    message = models.TextField("message")
    payload = models.JSONField("données", default=dict, blank=True)
    lu = models.BooleanField("lue", default=False)
    lu_le = models.DateTimeField("lue le", null=True, blank=True)

    class Meta:
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["destinataire", "lu", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.type} → {self.destinataire_id}"
