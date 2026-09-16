"""Authentification JWT : connexion, rafraîchissement, profil, déconnexion, comptes inactifs."""

import pytest

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login/"


def test_login_renvoie_les_jetons_et_le_profil(api_anonyme, distributeur):
    r = api_anonyme.post(LOGIN, {"email": "dist@test.fr", "password": "Motdepasse-Solide-1"}, format="json")
    assert r.status_code == 200, r.json()
    data = r.json()
    assert {"access", "refresh", "utilisateur"} <= set(data)
    assert data["utilisateur"]["role"] == "DISTRIBUTEUR" and data["utilisateur"]["email"] == "dist@test.fr"
    assert "password" not in data["utilisateur"]


def test_login_refuse_un_mauvais_mot_de_passe(api_anonyme, distributeur):
    r = api_anonyme.post(LOGIN, {"email": "dist@test.fr", "password": "faux"}, format="json")
    assert r.status_code == 401
    assert r.json()["code"]


def test_login_refuse_un_compte_inactif(api_anonyme, distributeur):
    distributeur.is_active = False
    distributeur.save(update_fields=["is_active"])
    r = api_anonyme.post(LOGIN, {"email": "dist@test.fr", "password": "Motdepasse-Solide-1"}, format="json")
    assert r.status_code == 401


def test_me_exige_un_jeton(api_anonyme, api_siege):
    assert api_anonyme.get("/api/v1/auth/me/").status_code == 401
    r = api_siege.get("/api/v1/auth/me/")
    assert r.status_code == 200 and r.json()["role"] == "SIEGE"


def test_refresh_fait_tourner_le_jeton_et_logout_le_revoque(api_anonyme, siege):
    jetons = api_anonyme.post(
        LOGIN, {"email": "siege@test.fr", "password": "Motdepasse-Solide-1"}, format="json"
    ).json()
    r = api_anonyme.post("/api/v1/auth/refresh/", {"refresh": jetons["refresh"]}, format="json")
    assert r.status_code == 200 and r.json()["access"] and r.json()["refresh"] != jetons["refresh"]
    # L'ancien jeton de rafraîchissement est mis en liste noire après rotation.
    assert api_anonyme.post("/api/v1/auth/refresh/", {"refresh": jetons["refresh"]}, format="json").status_code == 401
    nouveau = r.json()["refresh"]
    api_anonyme.credentials(HTTP_AUTHORIZATION=f"Bearer {r.json()['access']}")
    assert api_anonyme.post("/api/v1/auth/logout/", {"refresh": nouveau}, format="json").status_code in (200, 204, 205)
    api_anonyme.credentials()
    assert api_anonyme.post("/api/v1/auth/refresh/", {"refresh": nouveau}, format="json").status_code == 401
