"""
Serializer du FDR : validation en deux modes et normalisation des champs conditionnels.

* mode « brouillon » (sauvegarde) : tout est facultatif, mais toute valeur fournie doit
  respecter son format ; les règles croisées ne s'appliquent que si les deux membres sont
  renseignés. On ne bloque jamais l'enregistrement d'un travail en cours.
* mode « envoi » : tous les champs obligatoires sont exigés, plus les règles croisées.

La normalisation efface les champs devenus non pertinents (ex. `modification_structure`
lorsque le chantier n'est plus une rénovation) pour que la base reste cohérente.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings
from rest_framework import serializers

from apps.core.utils import nettoyer_texte

from ..choices import TypeChantier, TypeIntervention, Usage
from ..models import FDR

MODE_BROUILLON = "brouillon"
MODE_ENVOI = "envoi"

REGEX_CONTRAT = re.compile(r"^[A-Z0-9]{6,20}$")
REGEX_CODE_POSTAL = re.compile(r"^\d{5}$")
REGEX_SIRET = re.compile(r"^\d{14}$")
MONTANT_MAX = Decimal("9999999999.99")

# Champs obligatoires pour envoyer la demande au siège (les conditionnels sont traités à part).
CHAMPS_OBLIGATOIRES_ENVOI = (
    "assure_nom",
    "assure_adresse",
    "assure_code_postal",
    "assure_ville",
    "assure_siret",
    "numero_contrat",
    "chantier_nom",
    "chantier_ville",
    "type_chantier",
    "usage",
    "chantier_atypique",
    "date_debut",
    "date_fin",
    "cout_total",
    "description_travaux",
    "montant_prestation",
    "type_intervention",
    "activite_couverte",
    "travaux_standards",
)
# Tous les champs déclaratifs du FDR (hors clé de liaison et horodatage).
CHAMPS_FDR = tuple(f.name for f in FDR._meta.fields if f.name not in ("demande", "created_at", "updated_at"))
CHAMPS_TEXTE = (
    "assure_nom",
    "assure_adresse",
    "assure_ville",
    "reference_client",
    "chantier_nom",
    "chantier_ville",
    "usage_autre_precision",
    "description_travaux",
    "entreprise_principale_nom",
    "activite_non_couverte_precision",
)


def luhn_valide(chiffres: str) -> bool:
    """Contrôle de Luhn (SIRET / SIREN)."""
    total = 0
    for position, caractere in enumerate(reversed(chiffres)):
        n = int(caractere)
        if position % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


class FDRSerializer(serializers.ModelSerializer):
    """Lecture / écriture du FDR. Le mode de validation est passé via `context["mode"]`."""

    class Meta:
        model = FDR
        exclude = ["demande"]
        extra_kwargs = {
            "cout_total": {"min_value": Decimal("0.01"), "max_value": MONTANT_MAX, "coerce_to_string": True},
            "montant_prestation": {"min_value": Decimal("0.01"), "max_value": MONTANT_MAX, "coerce_to_string": True},
            # Saisie tolérée avec espaces de groupement (833 207 194 00014) : normalisée par validate_*.
            "assure_siret": {"max_length": 20},
            "assure_code_postal": {"max_length": 8},
        }

    # ------------------------------------------------------------------ helpers
    @property
    def mode(self) -> str:
        return self.context.get("mode", MODE_BROUILLON)

    def _valeur(self, attrs: dict[str, Any], champ: str) -> Any:
        """Valeur résultante d'un champ : payload si présent, sinon instance existante (PATCH)."""
        if champ in attrs:
            return attrs[champ]
        return getattr(self.instance, champ, None) if self.instance else None

    # ------------------------------------------------------------------ champs
    def validate_assure_code_postal(self, valeur: str | None) -> str | None:
        if valeur is None or valeur == "":
            return None
        valeur = valeur.replace(" ", "")
        if not REGEX_CODE_POSTAL.match(valeur):
            raise serializers.ValidationError("Le code postal doit comporter 5 chiffres.")
        return valeur

    def validate_assure_siret(self, valeur: str | None) -> str | None:
        """SIRET : 14 chiffres et clé de Luhn valide (identification de l'établissement assuré)."""
        if valeur is None or valeur == "":
            return None
        valeur = valeur.replace(" ", "")
        if not REGEX_SIRET.match(valeur):
            raise serializers.ValidationError("Le SIRET doit comporter 14 chiffres.")
        if not luhn_valide(valeur):
            raise serializers.ValidationError("Le SIRET est invalide (clé de contrôle).")
        return valeur

    def validate_numero_contrat(self, valeur: str | None) -> str | None:
        if valeur is None:
            return None
        normalise = valeur.upper().replace(" ", "").replace("-", "")
        if not REGEX_CONTRAT.match(normalise):
            raise serializers.ValidationError(
                "Le numéro de contrat doit comporter de 6 à 20 caractères alphanumériques."
            )
        return normalise

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:  # noqa: C901 – règles explicites
        erreurs: dict[str, str] = {}

        # Nettoyage des textes (caractères de contrôle, espaces) ; chaîne vide → None.
        for champ in CHAMPS_TEXTE:
            if champ in attrs:
                attrs[champ] = nettoyer_texte(attrs[champ]) or None

        # Fusion avec l'instance pour raisonner sur l'état résultant.
        etat = {champ: self._valeur(attrs, champ) for champ in CHAMPS_FDR}

        # --- Normalisation des champs conditionnels devenus non pertinents ---
        if etat["type_chantier"] != TypeChantier.RENOVATION:
            attrs["modification_structure"] = None
            etat["modification_structure"] = None
        if etat["usage"] != Usage.AUTRE:
            attrs["usage_autre_precision"] = None
            etat["usage_autre_precision"] = None
        if etat["activite_couverte"] is not False:
            attrs["activite_non_couverte_precision"] = None
            etat["activite_non_couverte_precision"] = None
        if etat["type_intervention"] != TypeIntervention.SOUS_TRAITANT:
            attrs["entreprise_principale_nom"] = None
            etat["entreprise_principale_nom"] = None

        # --- Règles croisées (appliquées dès que les deux membres sont connus) ---
        debut: date | None = etat["date_debut"]
        fin: date | None = etat["date_fin"]
        if debut and fin:
            if fin < debut:
                erreurs["date_fin"] = "La date de fin doit être postérieure ou égale à la date de début."
            elif (fin - debut).days > settings.METIER["FDR_DUREE_MAX_DAYS"]:
                erreurs["date_fin"] = "La durée du chantier ne peut pas dépasser 10 ans."

        cout = etat["cout_total"]
        prestation = etat["montant_prestation"]
        if cout is not None and prestation is not None and Decimal(prestation) > Decimal(cout):
            erreurs["montant_prestation"] = (
                "Le montant de la prestation ne peut pas dépasser le coût total du chantier."
            )

        if etat["usage_autre_precision"] and len(etat["usage_autre_precision"]) < 3:
            erreurs["usage_autre_precision"] = "Précisez l'usage (3 caractères minimum)."
        if etat["activite_non_couverte_precision"] and len(etat["activite_non_couverte_precision"]) < 10:
            erreurs["activite_non_couverte_precision"] = "Décrivez l'activité non couverte (10 caractères minimum)."

        # --- Mode envoi : obligations ---
        if self.mode == MODE_ENVOI:
            for champ in CHAMPS_OBLIGATOIRES_ENVOI:
                if etat[champ] in (None, ""):
                    erreurs.setdefault(champ, "Ce champ est obligatoire pour envoyer la demande.")
            if etat["type_chantier"] == TypeChantier.RENOVATION and etat["modification_structure"] is None:
                erreurs.setdefault("modification_structure", "Indiquez si la structure est modifiée.")
            if etat["usage"] == Usage.AUTRE and not etat["usage_autre_precision"]:
                erreurs.setdefault("usage_autre_precision", "Précisez l'usage de l'ouvrage.")
            if etat["activite_couverte"] is False and not etat["activite_non_couverte_precision"]:
                erreurs.setdefault(
                    "activite_non_couverte_precision", "Décrivez l'activité non couverte par le contrat."
                )
            if etat["description_travaux"] and len(etat["description_travaux"]) < 20:
                erreurs.setdefault(
                    "description_travaux", "Décrivez les travaux plus précisément (20 caractères minimum)."
                )
            if debut:
                aujourdhui = date.today()
                if debut < aujourdhui - timedelta(days=settings.METIER["FDR_DATE_DEBUT_MAX_PAST_DAYS"]):
                    erreurs.setdefault("date_debut", "La date de début ne peut pas être antérieure de plus d'un an.")
                elif debut > aujourdhui + timedelta(days=settings.METIER["FDR_DATE_DEBUT_MAX_FUTURE_DAYS"]):
                    erreurs.setdefault("date_debut", "La date de début ne peut pas être à plus de trois ans.")

        if erreurs:
            raise serializers.ValidationError(erreurs)
        return attrs


def valider_pour_envoi(fdr: FDR) -> dict[str, str]:
    """
    Rejoue la validation « envoi » sur un FDR existant sans le modifier.

    Renvoie un dictionnaire {champ: message} vide si le FDR peut être envoyé. Utilisé par
    l'endpoint de complétude (indicateur) et par le workflow d'envoi (blocage).
    """
    donnees = FDRSerializer(fdr).data
    serializer = FDRSerializer(instance=fdr, data=donnees, context={"mode": MODE_ENVOI})
    if serializer.is_valid():
        return {}
    return {champ: (msgs[0] if isinstance(msgs, list) else str(msgs)) for champ, msgs in serializer.errors.items()}
