"""Modèles des pièces justificatives."""

from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import ModeleUUID


def chemin_piece(instance: PieceJointe, filename: str) -> str:
    """
    Chemin de stockage d'une pièce : `demandes/<uuid demande>/<libellé-du-type>-<suffixe aléatoire>.<ext>`.

    Le fichier est stocké sous le libellé de son type (slugifié, donc sans caractère dangereux),
    complété d'un suffixe aléatoire pour éviter toute collision. Le nom fourni par le client
    n'entre JAMAIS dans le chemin (pas de traversée de répertoire) ; l'extension est celle validée
    par l'upload.
    """
    extension = Path(filename).suffix.lower()
    base = slugify(Path(instance.nom_fichier or "piece").stem) or "piece"
    return f"demandes/{instance.demande_id}/{base}-{uuid.uuid4().hex[:8]}{extension}"


class TypePiece(models.Model):
    """Référentiel des types de pièces (alimenté par migration depuis `catalogue.py`)."""

    code = models.CharField("code", max_length=40, primary_key=True)
    libelle = models.CharField("libellé", max_length=200)
    description = models.TextField("description", blank=True)
    ordre = models.PositiveSmallIntegerField("ordre d'affichage", default=0)

    class Meta:
        verbose_name = "type de pièce"
        verbose_name_plural = "types de pièces"
        ordering = ["ordre", "code"]

    def __str__(self) -> str:
        return self.libelle


class PieceJointeQuerySet(models.QuerySet["PieceJointe"]):
    def actives(self) -> PieceJointeQuerySet:
        """Pièces non supprimées (suppression logique)."""
        return self.filter(deleted_at__isnull=True)


class PieceJointe(ModeleUUID):
    """
    Fichier déposé par le distributeur pour une demande.

    La suppression est logique (`deleted_at`) afin de conserver l'historique des soumissions ;
    le fichier physique est purgé avec la demande.
    """

    demande = models.ForeignKey("demandes.Demande", on_delete=models.CASCADE, related_name="pieces")
    type_piece = models.ForeignKey(TypePiece, on_delete=models.PROTECT, related_name="pieces")
    fichier = models.FileField("fichier", upload_to=chemin_piece, max_length=255)
    # Nom métier de la pièce : libellé du type (+ numéro si plusieurs pièces du même type), avec extension.
    nom_fichier = models.CharField("nom de la pièce", max_length=255)
    # Nom du fichier tel que déposé par l'utilisateur (information / traçabilité uniquement).
    nom_original = models.CharField("nom d'origine", max_length=255)
    mime = models.CharField("type MIME", max_length=100)
    taille = models.PositiveBigIntegerField("taille (octets)")
    sha256 = models.CharField("empreinte SHA-256", max_length=64, db_index=True)
    deposee_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    deleted_at = models.DateTimeField("supprimée le", null=True, blank=True)

    objects = PieceJointeQuerySet.as_manager()

    class Meta:
        verbose_name = "pièce jointe"
        verbose_name_plural = "pièces jointes"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.nom_fichier} ({self.type_piece_id})"
