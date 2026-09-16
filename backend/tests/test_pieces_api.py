"""Upload sécurisé des pièces : types, contenu réel, doublons, droits, téléchargement."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from tests.conftest import PDF_MINIMAL

pytestmark = pytest.mark.django_db


def url(demande):
    return f"/api/v1/demandes/{demande.pk}/pieces/"


def png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, format="PNG")
    return buffer.getvalue()


def test_upload_pdf_ok_et_telechargement(api_distributeur, api_siege, demande_brouillon):
    fichier = SimpleUploadedFile("devis signé.pdf", PDF_MINIMAL, content_type="application/pdf")
    r = api_distributeur.post(
        url(demande_brouillon), {"fichier": fichier, "type_piece": "MARCHE_SIGNE"}, format="multipart"
    )
    assert r.status_code == 201, r.json()
    piece = r.json()
    assert piece["mime"] == "application/pdf" and piece["nom_original"] == "devis signé.pdf"
    # La pièce est renommée d'après le libellé de son type, à l'affichage comme sur le disque.
    assert piece["nom_fichier"] == "Devis accepté ou marché signé.pdf"
    from apps.pieces.models import PieceJointe

    assert "devis-accepte-ou-marche-signe-" in PieceJointe.objects.get(pk=piece["id"]).fichier.name
    r = api_siege.get(f"{url(demande_brouillon)}{piece['id']}/download/")
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf" and "attachment" in r["Content-Disposition"]
    assert "Devis" in r["Content-Disposition"]
    # Doublon (même contenu, même type) refusé…
    fichier = SimpleUploadedFile("copie.pdf", PDF_MINIMAL, content_type="application/pdf")
    r = api_distributeur.post(
        url(demande_brouillon), {"fichier": fichier, "type_piece": "MARCHE_SIGNE"}, format="multipart"
    )
    assert r.status_code == 409 and r.json()["code"] == "PIECE_DUPLIQUEE"
    # … mais le même fichier est accepté pour un autre type (renommé d'après ce type).
    fichier = SimpleUploadedFile("copie.pdf", PDF_MINIMAL, content_type="application/pdf")
    r = api_distributeur.post(url(demande_brouillon), {"fichier": fichier, "type_piece": "AUTRE"}, format="multipart")
    assert r.status_code == 201 and r.json()["nom_fichier"] == "Autre document.pdf"


def test_exe_renomme_en_pdf_refuse(api_distributeur, demande_brouillon):
    fichier = SimpleUploadedFile("virus.pdf", b"MZ\x90\x00" + b"\x00" * 100, content_type="application/pdf")
    r = api_distributeur.post(url(demande_brouillon), {"fichier": fichier, "type_piece": "AUTRE"}, format="multipart")
    assert r.status_code == 415 and r.json()["code"] == "TYPE_FICHIER_NON_AUTORISE"


def test_extension_interdite(api_distributeur, demande_brouillon):
    fichier = SimpleUploadedFile("script.exe", b"MZ", content_type="application/octet-stream")
    r = api_distributeur.post(url(demande_brouillon), {"fichier": fichier, "type_piece": "AUTRE"}, format="multipart")
    assert r.status_code == 415


def test_image_png_ok(api_distributeur, demande_brouillon):
    fichier = SimpleUploadedFile("photo.png", png_bytes(), content_type="image/png")
    r = api_distributeur.post(
        url(demande_brouillon), {"fichier": fichier, "type_piece": "PHOTOS_PLANS"}, format="multipart"
    )
    assert r.status_code == 201 and r.json()["mime"] == "image/png"


def test_fichier_trop_volumineux(api_distributeur, demande_brouillon, settings):
    settings.METIER["UPLOAD_MAX_BYTES"] = 100
    fichier = SimpleUploadedFile("gros.pdf", PDF_MINIMAL + b"\n" * 200, content_type="application/pdf")
    r = api_distributeur.post(url(demande_brouillon), {"fichier": fichier, "type_piece": "AUTRE"}, format="multipart")
    assert r.status_code == 413
    settings.METIER["UPLOAD_MAX_BYTES"] = 10 * 1024 * 1024


def test_droits_pieces(api_siege, api_autre_distributeur, demande_brouillon):
    fichier = SimpleUploadedFile("a.pdf", PDF_MINIMAL, content_type="application/pdf")
    assert (
        api_siege.post(
            url(demande_brouillon), {"fichier": fichier, "type_piece": "AUTRE"}, format="multipart"
        ).status_code
        == 403
    )
    fichier = SimpleUploadedFile("a.pdf", PDF_MINIMAL, content_type="application/pdf")
    assert (
        api_autre_distributeur.post(
            url(demande_brouillon), {"fichier": fichier, "type_piece": "AUTRE"}, format="multipart"
        ).status_code
        == 404
    )


def test_suppression_logique_et_changement_de_type(api_distributeur, demande_brouillon):
    fichier = SimpleUploadedFile("a.pdf", PDF_MINIMAL, content_type="application/pdf")
    pid = api_distributeur.post(
        url(demande_brouillon), {"fichier": fichier, "type_piece": "AUTRE"}, format="multipart"
    ).json()["id"]
    r = api_distributeur.patch(f"{url(demande_brouillon)}{pid}/", {"type_piece": "MARCHE_SIGNE"}, format="json")
    assert r.status_code == 200 and r.json()["type_piece"] == "MARCHE_SIGNE"
    assert r.json()["nom_fichier"] == "Devis accepté ou marché signé.pdf"
    from apps.pieces.models import PieceJointe

    piece = PieceJointe.objects.get(pk=pid)
    assert "devis-accepte-ou-marche-signe-" in piece.fichier.name and piece.fichier.storage.exists(piece.fichier.name)
    assert api_distributeur.delete(f"{url(demande_brouillon)}{pid}/").status_code == 204
    assert api_distributeur.get(url(demande_brouillon)).json() == []
    assert api_distributeur.get(f"{url(demande_brouillon)}{pid}/download/").status_code == 404
