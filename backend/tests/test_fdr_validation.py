"""Validation du FDR : modes brouillon / envoi, règles croisées, normalisation."""

from datetime import date, timedelta

import pytest

from apps.demandes.serializers.fdr import FDRSerializer, valider_pour_envoi
from tests.conftest import creer_demande

pytestmark = pytest.mark.django_db


def test_brouillon_accepte_partiel(demande_brouillon):
    s = FDRSerializer(demande_brouillon.fdr, data={"assure_nom": "  X  "}, partial=True, context={"mode": "brouillon"})
    assert s.is_valid(), s.errors
    assert s.validated_data["assure_nom"] == "X"


def test_brouillon_refuse_dates_inversees(demande_brouillon):
    s = FDRSerializer(
        demande_brouillon.fdr, data={"date_fin": date.today()}, partial=True, context={"mode": "brouillon"}
    )
    assert not s.is_valid() and "date_fin" in s.errors


def test_prestation_superieure_au_cout(demande_brouillon):
    s = FDRSerializer(
        demande_brouillon.fdr, data={"montant_prestation": "2000000.00"}, partial=True, context={"mode": "brouillon"}
    )
    assert not s.is_valid() and "montant_prestation" in s.errors


def test_numero_contrat_normalise_et_format(demande_brouillon):
    s = FDRSerializer(
        demande_brouillon.fdr, data={"numero_contrat": "rcd 2026-ly0142"}, partial=True, context={"mode": "brouillon"}
    )
    assert s.is_valid(), s.errors
    assert s.validated_data["numero_contrat"] == "RCD2026LY0142"
    s = FDRSerializer(demande_brouillon.fdr, data={"numero_contrat": "ab"}, partial=True, context={"mode": "brouillon"})
    assert not s.is_valid()


def test_normalisation_champs_conditionnels(distributeur):
    d = creer_demande(
        distributeur,
        type_chantier="RENOVATION",
        modification_structure=True,
        usage="AUTRE",
        usage_autre_precision="Halle",
        activite_couverte=False,
        activite_non_couverte_precision="Fluides médicaux xyz",
    )
    s = FDRSerializer(
        d.fdr,
        data={"type_chantier": "CONSTRUCTION_NEUVE", "usage": "BUREAU", "activite_couverte": True},
        partial=True,
        context={"mode": "brouillon"},
    )
    assert s.is_valid(), s.errors
    fdr = s.save()
    assert fdr.modification_structure is None
    assert fdr.usage_autre_precision is None
    assert fdr.activite_non_couverte_precision is None


def test_envoi_exige_les_obligatoires(distributeur):
    d = creer_demande(
        distributeur, assure_nom=None, assure_siret=None, type_chantier="RENOVATION", modification_structure=None
    )
    erreurs = valider_pour_envoi(d.fdr)
    assert "assure_nom" in erreurs and "assure_siret" in erreurs and "modification_structure" in erreurs


def test_envoi_usage_autre_sans_precision(distributeur):
    d = creer_demande(distributeur, usage="AUTRE", usage_autre_precision=None)
    assert "usage_autre_precision" in valider_pour_envoi(d.fdr)


def test_envoi_date_trop_ancienne(distributeur):
    d = creer_demande(distributeur, date_debut=date.today() - timedelta(days=400), date_fin=date.today())
    assert "date_debut" in valider_pour_envoi(d.fdr)


def test_fdr_valide_pret(distributeur):
    assert valider_pour_envoi(creer_demande(distributeur).fdr) == {}


def test_siret_et_code_postal(demande_brouillon):
    s = FDRSerializer(
        demande_brouillon.fdr,
        data={"assure_siret": "833 207 194 00014", "assure_code_postal": "69002"},
        partial=True,
        context={"mode": "brouillon"},
    )
    assert s.is_valid(), s.errors
    assert s.validated_data["assure_siret"] == "83320719400014"
    s = FDRSerializer(
        demande_brouillon.fdr, data={"assure_siret": "83320719400015"}, partial=True, context={"mode": "brouillon"}
    )
    assert not s.is_valid() and "assure_siret" in s.errors  # clé de Luhn invalide
    s = FDRSerializer(
        demande_brouillon.fdr, data={"assure_code_postal": "6900"}, partial=True, context={"mode": "brouillon"}
    )
    assert not s.is_valid() and "assure_code_postal" in s.errors
