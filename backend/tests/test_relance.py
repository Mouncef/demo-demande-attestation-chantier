"""Relance par email : statut requis, cooldown de 24 h, 429 avec Retry-After."""

from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from apps.demandes.models import Relance

pytestmark = pytest.mark.django_db
URL = "/api/v1/demandes/"


def test_relance_ok_puis_trop_tot(api_distributeur, demande_en_cours, siege, django_capture_on_commit_callbacks):
    mail.outbox.clear()
    # Les emails partent après commit : on exécute les callbacks `on_commit` dans le test.
    with django_capture_on_commit_callbacks(execute=True):
        r = api_distributeur.post(f"{URL}{demande_en_cours.pk}/relancer/", {"message": "Urgent"}, format="json")
    assert r.status_code == 201 and r.json()["email_ok"] is True
    assert len(mail.outbox) == 1 and siege.email in mail.outbox[0].to and "Urgent" in mail.outbox[0].body
    r = api_distributeur.post(f"{URL}{demande_en_cours.pk}/relancer/")
    assert r.status_code == 429 and r.json()["code"] == "RELANCE_TROP_TOT"
    assert int(r["Retry-After"]) > 0 and r.json()["prochaine_relance_possible"]
    assert api_distributeur.get(f"{URL}{demande_en_cours.pk}/").json()["nb_relances"] == 1


def test_relance_autorisee_apres_24h(api_distributeur, demande_en_cours):
    api_distributeur.post(f"{URL}{demande_en_cours.pk}/relancer/")
    Relance.objects.update(created_at=timezone.now() - timedelta(hours=25))
    assert api_distributeur.post(f"{URL}{demande_en_cours.pk}/relancer/").status_code == 201


def test_relance_refusee_hors_en_cours(api_distributeur, demande_brouillon):
    assert api_distributeur.post(f"{URL}{demande_brouillon.pk}/relancer/").status_code == 409


def test_relance_interdite_au_siege(api_siege, demande_en_cours):
    assert api_siege.post(f"{URL}{demande_en_cours.pk}/relancer/").status_code == 403
