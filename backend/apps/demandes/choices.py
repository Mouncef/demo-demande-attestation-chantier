"""Énumérations métier des demandes et du FDR."""

from django.db import models


class Statut(models.TextChoices):
    """
    Cycle de vie d'une demande.

    BROUILLON → EN_COURS → TRAITE, avec l'état intermédiaire A_COMPLETER lorsque le siège
    demande des éléments complémentaires (la main revient au distributeur).
    """

    BROUILLON = "BROUILLON", "Brouillon"
    EN_COURS = "EN_COURS", "En cours d'instruction"
    A_COMPLETER = "A_COMPLETER", "Compléments demandés"
    TRAITE = "TRAITE", "Traitée"


class Decision(models.TextChoices):
    ACCEPTEE = "ACCEPTEE", "Acceptée"
    REFUSEE = "REFUSEE", "Refusée"


class TypeChantier(models.TextChoices):
    CONSTRUCTION_NEUVE = "CONSTRUCTION_NEUVE", "Construction neuve"
    RENOVATION = "RENOVATION", "Rénovation"


class Usage(models.TextChoices):
    HABITATION = "HABITATION", "Habitation"
    BUREAU = "BUREAU", "Bureau"
    COMMERCE = "COMMERCE", "Commerce"
    AUTRE = "AUTRE", "Autre"


class TypeIntervention(models.TextChoices):
    ENTREPRISE_PRINCIPALE = "ENTREPRISE_PRINCIPALE", "Entreprise principale"
    SOUS_TRAITANT = "SOUS_TRAITANT", "Sous-traitant"


class NiveauRisque(models.TextChoices):
    FAIBLE = "FAIBLE", "Faible"
    MODERE = "MODERE", "Modéré"
    ELEVE = "ELEVE", "Élevé"


class ActionHistorique(models.TextChoices):
    """Actions journalisées dans l'historique d'une demande."""

    CREATION = "CREATION", "Création"
    ENVOI = "ENVOI", "Envoi au siège"
    RENVOI = "RENVOI", "Renvoi après compléments"
    COMPLEMENTS = "COMPLEMENTS", "Compléments demandés"
    ACCEPTATION = "ACCEPTATION", "Acceptation"
    REFUS = "REFUS", "Refus"
    RELANCE = "RELANCE", "Relance"
    ATTESTATION_PROJET_VALIDEE = "ATTESTATION_PROJET_VALIDEE", "Projet d'attestation validé (ancien circuit)"
    ATTESTATION_PROJET_SOUMISE = "ATTESTATION_PROJET_SOUMISE", "Projet d'attestation soumis au siège"
    ATTESTATION_PROJET_A_CORRIGER = "ATTESTATION_PROJET_A_CORRIGER", "Projet d'attestation renvoyé pour correction"
    ATTESTATION_PROJET_ROUVERTE = "ATTESTATION_PROJET_ROUVERTE", "Projet d'attestation repris par le distributeur"
    ATTESTATION_DEFINITIVE_VALIDEE = "ATTESTATION_DEFINITIVE_VALIDEE", "Attestation définitive validée"
