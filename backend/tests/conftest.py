"""Fixtures partagées : utilisateurs par rôle et clients API authentifiés."""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.comptes.models import Role, User


@pytest.fixture
def distributeur(db) -> User:
    return User.objects.create_user(
        "dist@test.fr",
        "Motdepasse-Solide-1",
        role=Role.DISTRIBUTEUR,
        first_name="Claire",
        last_name="Martin",
        organisation="Agence Test",
    )


@pytest.fixture
def autre_distributeur(db) -> User:
    return User.objects.create_user("dist2@test.fr", "Motdepasse-Solide-1", role=Role.DISTRIBUTEUR)


@pytest.fixture
def siege(db) -> User:
    return User.objects.create_user(
        "siege@test.fr", "Motdepasse-Solide-1", role=Role.SIEGE, first_name="Sophie", last_name="Durand"
    )


def _client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def api_distributeur(distributeur) -> APIClient:
    return _client(distributeur)


@pytest.fixture
def api_autre_distributeur(autre_distributeur) -> APIClient:
    return _client(autre_distributeur)


@pytest.fixture
def api_siege(siege) -> APIClient:
    return _client(siege)


@pytest.fixture
def api_anonyme() -> APIClient:
    return APIClient()
