"""Modèles des demandes d'attestation et du Formulaire de Déclaration du Risque (FDR)."""

from __future__ import annotations

from django.conf import settings
from django.db import models, transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.core.models import ModeleHorodate, ModeleUUID

from .choices import ActionHistorique, Decision, Statut, TypeChantier, TypeIntervention, Usage


class CompteurReference(models.Model):
    """Compteur annuel utilisé pour générer des références lisibles (DEM-2026-000001)."""

    prefixe = models.CharField(max_length=10)
    annee = models.PositiveIntegerField()
    valeur = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("prefixe", "annee")]

    def __str__(self) -> str:
        return f"{self.prefixe}-{self.annee}: {self.valeur}"

    @classmethod
    def suivant(cls, prefixe: str) -> str:
        """Renvoie la prochaine référence de façon atomique (verrou de ligne)."""
        annee = timezone.now().year
        with transaction.atomic():
            compteur, _ = cls.objects.select_for_update().get_or_create(prefixe=prefixe, annee=annee)
            compteur.valeur = F("valeur") + 1
            compteur.save(update_fields=["valeur"])
            compteur.refresh_from_db()
        return f"{prefixe}-{annee}-{compteur.valeur:06d}"


class Demande(ModeleUUID):
    """
    Demande d'attestation de chantier.

    Porte le statut, la décision du siège, les commentaires et les métadonnées de suivi.
    Les données déclaratives sont dans `FDR` (relation un-à-un).
    """

    reference = models.CharField("référence", max_length=20, unique=True, editable=False)
    distributeur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="demandes",
        verbose_name="distributeur",
    )
    statut = models.CharField("statut", max_length=20, choices=Statut.choices, default=Statut.BROUILLON, db_index=True)
    decision = models.CharField(
        "décision", max_length=20, choices=Decision.choices, null=True, blank=True, db_index=True
    )

    commentaire_distributeur = models.TextField("commentaire du distributeur", blank=True)
    commentaire_siege = models.TextField("commentaire du siège", blank=True)
    motif_refus = models.TextField("motif du refus", blank=True)
    message_complements = models.TextField("éléments complémentaires demandés", blank=True)

    submitted_at = models.DateTimeField("dernier envoi au siège", null=True, blank=True)
    first_submitted_at = models.DateTimeField("premier envoi au siège", null=True, blank=True)
    nb_soumissions = models.PositiveSmallIntegerField("nombre d'envois", default=0)
    decided_at = models.DateTimeField("date de décision", null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    # Verrou optimiste : incrémenté à chaque modification du FDR, comparé au `version` envoyé par le client.
    version = models.PositiveIntegerField("version", default=1)
    # Score de risque figé au moment du dernier envoi (le siège instruit sur des données stables).
    scoring_snapshot = models.JSONField("scoring au dernier envoi", null=True, blank=True)

    class Meta:
        verbose_name = "demande"
        verbose_name_plural = "demandes"
        ordering = ["-created_at"]
        constraints = [
            # Une décision n'existe que pour une demande traitée.
            models.CheckConstraint(
                condition=Q(decision__isnull=True) | Q(statut=Statut.TRAITE),
                name="decision_uniquement_si_traitee",
            ),
        ]

    def __str__(self) -> str:
        return self.reference

    def save(self, *args, **kwargs) -> None:
        if not self.reference:
            self.reference = CompteurReference.suivant("DEM")
        super().save(*args, **kwargs)

    # --- Prédicats d'état utilisés par les services et les serializers ---------------
    @property
    def est_editable(self) -> bool:
        """Le distributeur peut modifier le FDR et les pièces."""
        return self.statut in (Statut.BROUILLON, Statut.A_COMPLETER)

    @property
    def est_traitee(self) -> bool:
        return self.statut == Statut.TRAITE

    @property
    def est_acceptee(self) -> bool:
        return self.est_traitee and self.decision == Decision.ACCEPTEE


class FDR(ModeleHorodate):
    """
    Formulaire de Déclaration du Risque.

    Tous les champs sont nullables pour permettre la sauvegarde d'un brouillon incomplet ;
    l'obligation est vérifiée par le serializer en « mode envoi ».
    """

    demande = models.OneToOneField(Demande, on_delete=models.CASCADE, related_name="fdr", primary_key=True)

    # --- L'assuré ---
    assure_nom = models.CharField("nom / raison sociale", max_length=200, null=True, blank=True)
    assure_adresse = models.CharField("adresse de l'assuré", max_length=200, null=True, blank=True)
    assure_code_postal = models.CharField("code postal de l'assuré", max_length=5, null=True, blank=True)
    assure_ville = models.CharField("ville de l'assuré", max_length=100, null=True, blank=True)
    assure_siret = models.CharField("SIRET de l'assuré", max_length=14, null=True, blank=True)
    numero_contrat = models.CharField("numéro de contrat", max_length=20, null=True, blank=True)
    reference_client = models.CharField("référence client", max_length=30, null=True, blank=True)

    # --- Le chantier ---
    chantier_nom = models.CharField("nom du chantier", max_length=200, null=True, blank=True)
    chantier_ville = models.CharField("ville du chantier", max_length=100, null=True, blank=True)
    type_chantier = models.CharField(
        "type de chantier", max_length=30, choices=TypeChantier.choices, null=True, blank=True
    )
    modification_structure = models.BooleanField("modification de structure", null=True, blank=True)
    usage = models.CharField("usage", max_length=20, choices=Usage.choices, null=True, blank=True)
    usage_autre_precision = models.CharField("précision de l'usage", max_length=200, null=True, blank=True)
    chantier_atypique = models.BooleanField("chantier atypique", null=True, blank=True)
    date_debut = models.DateField("date de début", null=True, blank=True)
    date_fin = models.DateField("date de fin", null=True, blank=True)
    cout_total = models.DecimalField("coût total (€)", max_digits=14, decimal_places=2, null=True, blank=True)

    # --- L'intervention ---
    description_travaux = models.TextField("description des travaux", null=True, blank=True)
    montant_prestation = models.DecimalField(
        "montant de la prestation (€)", max_digits=14, decimal_places=2, null=True, blank=True
    )
    type_intervention = models.CharField(
        "type d'intervention", max_length=30, choices=TypeIntervention.choices, null=True, blank=True
    )
    entreprise_principale_nom = models.CharField("entreprise principale", max_length=200, null=True, blank=True)
    activite_couverte = models.BooleanField("activité couverte par le contrat", null=True, blank=True)
    activite_non_couverte_precision = models.TextField("précision sur l'activité non couverte", null=True, blank=True)
    travaux_standards = models.BooleanField("travaux standards", null=True, blank=True)

    class Meta:
        verbose_name = "FDR"
        verbose_name_plural = "FDR"
        constraints = [
            models.CheckConstraint(
                condition=Q(date_fin__isnull=True) | Q(date_debut__isnull=True) | Q(date_fin__gte=F("date_debut")),
                name="fdr_date_fin_apres_debut",
            ),
            models.CheckConstraint(
                condition=Q(cout_total__isnull=True) | Q(cout_total__gt=0), name="fdr_cout_total_positif"
            ),
            models.CheckConstraint(
                condition=Q(montant_prestation__isnull=True) | Q(montant_prestation__gt=0),
                name="fdr_montant_prestation_positif",
            ),
        ]

    def __str__(self) -> str:
        return f"FDR {self.demande_id}"


class SoumissionFDR(ModeleHorodate):
    """
    Photographie du dossier à chaque envoi au siège.

    Conserve le PDF du FDR, les données déclarées, la liste des pièces et le scoring tels
    qu'ils étaient au moment de l'envoi : le siège instruit sur une base stable et l'historique
    des renvois reste consultable.
    """

    demande = models.ForeignKey(Demande, on_delete=models.CASCADE, related_name="soumissions")
    numero = models.PositiveSmallIntegerField("numéro d'envoi")
    pdf = models.FileField("PDF du FDR", upload_to="soumissions/%Y/%m/", max_length=255)
    fdr_snapshot = models.JSONField("FDR déclaré")
    pieces_snapshot = models.JSONField("pièces jointes")
    scoring_snapshot = models.JSONField("scoring")
    commentaire_distributeur = models.TextField(blank=True)

    class Meta:
        verbose_name = "soumission"
        verbose_name_plural = "soumissions"
        ordering = ["numero"]
        unique_together = [("demande", "numero")]

    def __str__(self) -> str:
        return f"{self.demande.reference} – envoi n°{self.numero}"


class HistoriqueTransition(ModeleHorodate):
    """Journal d'audit des actions sur une demande (qui, quand, quoi, de → vers)."""

    demande = models.ForeignKey(Demande, on_delete=models.CASCADE, related_name="historique")
    action = models.CharField("action", max_length=40, choices=ActionHistorique.choices)
    de_statut = models.CharField(max_length=20, choices=Statut.choices, null=True, blank=True)
    vers_statut = models.CharField(max_length=20, choices=Statut.choices, null=True, blank=True)
    decision = models.CharField(max_length=20, choices=Decision.choices, null=True, blank=True)
    acteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    commentaire = models.TextField(blank=True)

    class Meta:
        verbose_name = "événement d'historique"
        verbose_name_plural = "historique"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.demande_id} {self.action}"


class Relance(ModeleHorodate):
    """Relance du siège envoyée par le distributeur (email + notification)."""

    demande = models.ForeignKey(Demande, on_delete=models.CASCADE, related_name="relances")
    envoyee_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    message = models.TextField("message", blank=True)
    destinataires = models.JSONField("destinataires", default=list)
    email_ok = models.BooleanField("email envoyé", default=False)

    class Meta:
        verbose_name = "relance"
        verbose_name_plural = "relances"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Relance {self.demande_id} – {self.created_at:%d/%m/%Y %H:%M}"
