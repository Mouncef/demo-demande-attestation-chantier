"""Modèles abstraits partagés par toutes les apps."""

import uuid

from django.db import models


class ModeleHorodate(models.Model):
    """Ajoute les dates de création et de dernière modification."""

    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    class Meta:
        abstract = True


class ModeleUUID(ModeleHorodate):
    """
    Clé primaire UUID v4.

    Les identifiants exposés dans l'API ne sont donc pas prédictibles : un utilisateur ne peut
    pas énumérer les ressources en incrémentant un entier.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True
