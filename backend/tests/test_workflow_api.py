"""Machine à états, droits par rôle, isolation des données (via l'API)."""

from decimal import Decimal

import pytest
from django.core import mail

from apps.demandes.models import Demande
from apps.notifications.models import Notification
from tests.conftest import ajouter_piece, creer_demande

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
    assert "envoyer" in data["actions_possibles"] and "supprimer" in data["actions_possibles"]


def test_isolation_404_pour_autre_distributeur(api_autre_distributeur, demande_brouillon):
    assert api_autre_distributeur.get(f"{URL}{demande_brouillon.pk}/").status_code == 404
    assert api_autre_distributeur.patch(f"{URL}{demande_brouillon.pk}/fdr/", {"assure_nom": "X"}).status_code == 404
    assert api_autre_distributeur.get(URL).json()["count"] == 0


def test_siege_voit_tout(api_siege, demande_brouillon):
    assert api_siege.get(URL).json()["count"] == 1


def test_distributeur_ne_peut_pas_accepter(api_distributeur, demande_en_cours):
    r = api_distributeur.post(f"{URL}{demande_en_cours.pk}/accepter/")
    assert r.status_code == 403


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


def test_envoi_bloque_si_incomplet(api_distributeur, distributeur):
    d = creer_demande(distributeur, chantier_atypique=True)
    r = api_distributeur.post(f"{URL}{d.pk}/envoyer/")
    assert r.status_code == 409 and r.json()["code"] == "DOSSIER_INCOMPLET"
    assert set(r.json()["manquants"]) == {"DESCRIPTIF_TECHNIQUE", "PHOTOS_PLANS"}
    r = api_distributeur.get(f"{URL}{d.pk}/completude/")
    assert r.json()["complet"] is False and r.json()["pret_pour_envoi"] is False


def test_envoi_bloque_si_fdr_invalide(api_distributeur, distributeur):
    d = creer_demande(distributeur, assure_nom=None)
    r = api_distributeur.post(f"{URL}{d.pk}/envoyer/")
    assert r.status_code == 400 and "assure_nom" in r.json()["errors"]


def test_envoi_complet_effets(api_distributeur, distributeur, siege, django_capture_on_commit_callbacks):
    d = creer_demande(distributeur, chantier_atypique=True)
    ajouter_piece(d, "DESCRIPTIF_TECHNIQUE", distributeur, "a.pdf")
    ajouter_piece(d, "PHOTOS_PLANS", distributeur, "b.pdf")
    with django_capture_on_commit_callbacks(execute=True):
        r = api_distributeur.post(f"{URL}{d.pk}/envoyer/", {"commentaire": "Merci"}, format="json")
    assert r.status_code == 200, r.json()
    data = r.json()
    assert (
        data["statut"] == "EN_COURS"
        and data["nb_soumissions"] == 1
        and data["niveau_risque"] in {"FAIBLE", "MODERE", "ELEVE"}
    )
    assert "relancer" in data["actions_possibles"] and "envoyer" not in data["actions_possibles"]
    # PDF de la soumission, notification et email au siège
    assert api_distributeur.get(f"{URL}{d.pk}/soumissions/1/pdf/").status_code == 200
    assert Notification.objects.filter(destinataire=siege, type="DEMANDE_ENVOYEE").exists()
    assert len(mail.outbox) == 1 and siege.email in mail.outbox[0].to
    # Double envoi → 409
    assert api_distributeur.post(f"{URL}{d.pk}/envoyer/").status_code == 409
    # FDR figé
    assert api_distributeur.patch(f"{URL}{d.pk}/fdr/", {"assure_nom": "X"}, format="json").status_code == 409


def test_cycle_complements_puis_acceptation(api_distributeur, api_siege, demande_en_cours, distributeur):
    pk = demande_en_cours.pk
    assert api_siege.post(f"{URL}{pk}/demander-complements/", {"message": "court"}, format="json").status_code == 400
    r = api_siege.post(
        f"{URL}{pk}/demander-complements/", {"message": "Merci de joindre le devis signé."}, format="json"
    )
    assert r.status_code == 200 and r.json()["statut"] == "A_COMPLETER"
    assert Notification.objects.filter(destinataire=distributeur, type="COMPLEMENTS_DEMANDES").exists()
    # Le siège ne peut plus décider tant que la demande n'est pas renvoyée
    assert api_siege.post(f"{URL}{pk}/accepter/").status_code == 409
    # Le distributeur modifie et renvoie
    assert (
        api_distributeur.patch(f"{URL}{pk}/fdr/", {"assure_nom": "SAS BÂTI-RHÔNE 2"}, format="json").status_code == 200
    )
    r = api_distributeur.post(f"{URL}{pk}/envoyer/")
    assert r.status_code == 200 and r.json()["nb_soumissions"] == 2 and r.json()["statut"] == "EN_COURS"
    r = api_siege.post(f"{URL}{pk}/accepter/", {"commentaire": "OK"}, format="json")
    assert r.status_code == 200 and r.json()["statut"] == "TRAITE" and r.json()["decision"] == "ACCEPTEE"
    assert "editer_attestation_definitive" in r.json()["actions_possibles"]
    assert Notification.objects.filter(destinataire=distributeur, type="DEMANDE_TRAITEE").exists()
    # Terminal : plus aucune transition
    assert api_siege.post(f"{URL}{pk}/refuser/", {"motif": "Trop tard pour refuser"}, format="json").status_code == 409
    historique = api_siege.get(f"{URL}{pk}/historique/").json()
    assert [h["action"] for h in historique] == ["CREATION", "ENVOI", "COMPLEMENTS", "RENVOI", "ACCEPTATION"]


def test_refus_motif_obligatoire(api_siege, demande_en_cours):
    pk = demande_en_cours.pk
    assert api_siege.post(f"{URL}{pk}/refuser/", {}, format="json").status_code == 400
    r = api_siege.post(f"{URL}{pk}/refuser/", {"motif": "Activité non souscrite au contrat."}, format="json")
    assert r.status_code == 200 and r.json()["decision"] == "REFUSEE" and r.json()["motif_refus"]


def test_suppression_brouillon_uniquement(api_distributeur, demande_brouillon, demande_en_cours):
    assert api_distributeur.delete(f"{URL}{demande_brouillon.pk}/").status_code == 204
    assert not Demande.objects.filter(pk=demande_brouillon.pk).exists()
    assert api_distributeur.delete(f"{URL}{demande_en_cours.pk}/").status_code == 409


def test_filtres_liste(api_siege, demande_brouillon, demande_en_cours):
    assert api_siege.get(URL, {"statut": "EN_COURS"}).json()["count"] == 1
    assert api_siege.get(URL, {"statut": ["BROUILLON", "EN_COURS"]}).json()["count"] == 2
    assert api_siege.get(URL, {"search": "Terrasses"}).json()["count"] == 2


def test_lecture_fdr(api_distributeur, demande_brouillon):
    r = api_distributeur.get(f"{URL}{demande_brouillon.pk}/fdr/")
    assert r.status_code == 200 and r.json()["assure_nom"] == "SAS BÂTI-RHÔNE"


def test_completude_et_scoring(api_distributeur, distributeur):
    d = creer_demande(distributeur, chantier_atypique=True)
    r = api_distributeur.get(f"{URL}{d.pk}/completude/").json()
    assert r["complet"] is False and set(r["manquants"]) == {"DESCRIPTIF_TECHNIQUE", "PHOTOS_PLANS"}
    assert r["fdr_valide"] is True and r["pret_pour_envoi"] is False
    ajouter_piece(d, "DESCRIPTIF_TECHNIQUE", distributeur, "a.pdf")
    ajouter_piece(d, "PHOTOS_PLANS", distributeur, "b.pdf")
    r = api_distributeur.get(f"{URL}{d.pk}/completude/").json()
    assert r["complet"] is True and r["pret_pour_envoi"] is True
    s = api_distributeur.get(f"{URL}{d.pk}/scoring/").json()
    assert s["niveau"] in {"FAIBLE", "MODERE", "ELEVE"} and 0 <= s["score"] <= 100


def test_referentiels(api_distributeur):
    ref = api_distributeur.get("/api/v1/referentiels/").json()
    assert {c["code"] for c in ref["types_chantier"]} == {"CONSTRUCTION_NEUVE", "RENOVATION"}
    assert len(ref["types_pieces"]) == 12 and Decimal(ref["seuil_gros_chantier"]) == Decimal("10000000.00")
    assert ".pdf" in ref["upload"]["extensions"]
