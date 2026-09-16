"""Fixtures partagées : utilisateurs par rôle, clients API authentifiés, fabrique de demandes."""

from __future__ import annotations

import shutil
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.comptes.models import Role, User
from apps.demandes.models import Demande
from apps.demandes.services import workflow
from apps.pieces.models import PieceJointe, TypePiece

PDF_MINIMAL = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000101 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n160\n%%EOF\n"
)


@pytest.fixture(autouse=True, scope="session")
def _nettoyage_media():
    """Supprime le répertoire média de test en fin de session."""
    yield
    shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)


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


FDR_VALIDE = {
    "assure_nom": "SAS BÂTI-RHÔNE",
    "assure_adresse": "14 quai Perrache",
    "assure_code_postal": "69002",
    "assure_ville": "Lyon",
    "assure_siret": "83320719400014",
    "numero_contrat": "RCD2026LY0142",
    "chantier_nom": "Résidence Les Terrasses",
    "chantier_ville": "Villeurbanne",
    "type_chantier": "CONSTRUCTION_NEUVE",
    "usage": "HABITATION",
    "chantier_atypique": False,
    "date_debut": date.today() + timedelta(days=30),
    "date_fin": date.today() + timedelta(days=400),
    "cout_total": Decimal("1850000.00"),
    "montant_prestation": Decimal("420000.00"),
    "type_intervention": "ENTREPRISE_PRINCIPALE",
    "activite_couverte": True,
    "travaux_standards": True,
    "description_travaux": "Gros œuvre et maçonnerie d'un immeuble de 24 logements en R+4.",
}


def creer_demande(user: User, **fdr) -> Demande:
    """Crée une demande en brouillon avec un FDR valide (surchargeable)."""
    demande = workflow.creer_demande(user)
    valeurs = {**FDR_VALIDE, **fdr}
    for champ, valeur in valeurs.items():
        setattr(demande.fdr, champ, valeur)
    demande.fdr.save()
    return demande


def ajouter_piece(demande: Demande, code: str, user: User, nom: str = "piece.pdf") -> PieceJointe:
    import hashlib

    from django.core.files.base import ContentFile

    type_piece = TypePiece.objects.get(code=code)
    piece = PieceJointe(
        demande=demande,
        type_piece=type_piece,
        nom_fichier=f"{type_piece.libelle}.pdf",
        nom_original=nom,
        mime="application/pdf",
        taille=len(PDF_MINIMAL),
        deposee_par=user,
        sha256=hashlib.sha256(PDF_MINIMAL + nom.encode()).hexdigest(),
    )
    piece.fichier.save("piece.pdf", ContentFile(PDF_MINIMAL), save=True)
    return piece


@pytest.fixture
def demande_brouillon(distributeur) -> Demande:
    return creer_demande(distributeur)


@pytest.fixture
def demande_en_cours(distributeur) -> Demande:
    demande = creer_demande(distributeur)
    return workflow.envoyer(demande.pk, distributeur)


@pytest.fixture
def demande_acceptee(distributeur, siege) -> Demande:
    demande = creer_demande(distributeur)
    workflow.envoyer(demande.pk, distributeur)
    return workflow.accepter(demande.pk, siege)
