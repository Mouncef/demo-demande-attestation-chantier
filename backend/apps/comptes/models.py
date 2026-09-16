"""Modèle utilisateur : identification par email et rôle métier."""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class Role(models.TextChoices):
    """Rôles métier de la plateforme."""

    DISTRIBUTEUR = "DISTRIBUTEUR", "Distributeur (agent général / courtier)"
    SIEGE = "SIEGE", "Siège"


class UserManager(BaseUserManager["User"]):
    """Manager créant les utilisateurs à partir de l'email (pas de `username`)."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra: object) -> User:
        if not email:
            raise ValueError("L'adresse email est obligatoire.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra: object) -> User:
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email: str, password: str | None = None, **extra: object) -> User:
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", Role.SIEGE)
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    """
    Utilisateur de la plateforme.

    * `email` est l'identifiant de connexion (unique, insensible à la casse) ;
    * `role` détermine les droits (voir `apps.core.permissions`) ;
    * `organisation` est le cabinet / l'agence du distributeur, imprimé sur les attestations.
    """

    username = None  # type: ignore[assignment]
    email = models.EmailField("adresse email", unique=True)
    role = models.CharField("rôle", max_length=20, choices=Role.choices, default=Role.DISTRIBUTEUR)
    organisation = models.CharField("organisation", max_length=200, blank=True)
    code_distributeur = models.CharField("code distributeur", max_length=30, blank=True)
    # Coordonnées de l'intermédiaire imprimées en en-tête des attestations (« Votre Intermédiaire »).
    adresse = models.TextField("adresse", blank=True)
    telephone = models.CharField("téléphone", max_length=30, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()  # type: ignore[misc]

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"
        ordering = ["email"]

    def __str__(self) -> str:
        return f"{self.get_full_name() or self.email} ({self.get_role_display()})"

    @property
    def est_siege(self) -> bool:
        return self.role == Role.SIEGE

    @property
    def est_distributeur(self) -> bool:
        return self.role == Role.DISTRIBUTEUR

    @property
    def nom_affichage(self) -> str:
        """Nom lisible pour les emails, notifications et documents."""
        return self.get_full_name() or self.email
