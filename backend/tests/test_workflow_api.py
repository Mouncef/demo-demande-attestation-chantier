"""Demandes : création, droits par rôle, isolation des données, FDR (via l'API)."""

from decimal import Decimal

import pytest

from apps.demandes.models import Demande
from tests.conftest import creer_demande

pytestmark = pytest.mark.django_db
URL = "/api/v1/demandes/"


def test_anonyme_401(api_anonyme):
    assert api_anonyme.get(URL).status_code == 401


def test_siege_ne_cree_pas(api_siege):
    r = api_siege.post(URL)
    assert r.status_code == 403 and r.json()["code"] == "INTERDIT"


def test_creation_brouillon(api_distributeur):
    r = api_distributeur.post(URL)
    assert r.status_code == 201
    data = r.json()
    assert data["statut"] == "BROUILLON" and data["reference"].startswith("DEM-")
    assert "modifier_fdr" in data["actions_possibles"] and "supprimer" in data["actions_possibles"]
    assert Demande.objects.get(pk=data["id"]).historique.count() == 1


def test_isolation_404_pour_autre_distributeur(api_autre_distributeur, demande_brouillon):
    assert api_autre_distributeur.get(f"{URL}{demande_brouillon.pk}/").status_code == 404
    assert api_autre_distributeur.patch(f"{URL}{demande_brouillon.pk}/fdr/", {"assure_nom": "X"}).status_code == 404
    assert api_autre_distributeur.get(URL).json()["count"] == 0


def test_siege_voit_tout(api_siege, demande_brouillon):
    assert api_siege.get(URL).json()["count"] == 1
    assert api_siege.get(f"{URL}{demande_brouillon.pk}/").json()["actions_possibles"] == []


def test_patch_fdr_et_verrou_optimiste(api_distributeur, demande_brouillon):
    r = api_distributeur.patch(
        f"{URL}{demande_brouillon.pk}/fdr/", {"assure_nom": "Nouveau", "version": 1}, format="json"
    )
    assert r.status_code == 200 and r.json()["fdr"]["assure_nom"] == "Nouveau" and r.json()["version"] == 2
    r = api_distributeur.patch(
        f"{URL}{demande_brouillon.pk}/fdr/", {"assure_nom": "Périmé", "version": 1}, format="json"
    )
    assert r.status_code == 409 and r.json()["code"] == "CONFLIT_VERSION"


def test_patch_fdr_erreur_400_detaillee(api_distributeur, demande_brouillon):
    r = api_distributeur.patch(f"{URL}{demande_brouillon.pk}/fdr/", {"montant_prestation": "9999999.00"}, format="json")
    assert r.status_code == 400 and "montant_prestation" in r.json()["errors"]


def test_lecture_fdr(api_distributeur, demande_brouillon):
    r = api_distributeur.get(f"{URL}{demande_brouillon.pk}/fdr/")
    assert r.status_code == 200 and r.json()["assure_nom"] == "SAS BÂTI-RHÔNE"


def test_suppression_brouillon(api_distributeur, demande_brouillon):
    assert api_distributeur.delete(f"{URL}{demande_brouillon.pk}/").status_code == 204
    assert not Demande.objects.filter(pk=demande_brouillon.pk).exists()


def test_filtres_et_recherche(api_siege, distributeur, autre_distributeur):
    creer_demande(distributeur)
    creer_demande(autre_distributeur, chantier_nom="Gymnase municipal")
    assert api_siege.get(URL, {"statut": "BROUILLON"}).json()["count"] == 2
    assert api_siege.get(URL, {"statut": "EN_COURS"}).json()["count"] == 0
    assert api_siege.get(URL, {"search": "Terrasses"}).json()["count"] == 1
    assert api_siege.get(URL, {"distributeur": autre_distributeur.id}).json()["count"] == 1


def test_referentiels(api_distributeur):
    ref = api_distributeur.get("/api/v1/referentiels/").json()
    assert {c["code"] for c in ref["types_chantier"]} == {"CONSTRUCTION_NEUVE", "RENOVATION"}
    assert Decimal(ref["seuil_gros_chantier"]) == Decimal("10000000.00")
