"""
Validation de sécurité des fichiers déposés.

Défense en profondeur :
  1. extension du nom d'origine dans la liste blanche ;
  2. `Content-Type` déclaré par le client cohérent ;
  3. type réel détecté par libmagic sur le contenu (un `.exe` renommé `.pdf` est refusé) ;
  4. validation structurelle : Pillow pour les images (et limite de dimensions contre les
     bombes de décompression), pypdf pour les PDF (rejet des PDF chiffrés ou contenant du
     JavaScript / une action d'ouverture automatique) ;
  5. taille maximale.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

import magic
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from PIL import Image
from pypdf import PdfReader

from apps.core.exceptions import FichierTropVolumineux, TypeFichierNonAutorise

logger = logging.getLogger("securite")

# extension → types MIME acceptés pour cette extension
TYPES_AUTORISES: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
}
TYPES_OFFICE: dict[str, set[str]] = {
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
}
DIMENSION_IMAGE_MAX = 10_000  # pixels, par côté
Image.MAX_IMAGE_PIXELS = DIMENSION_IMAGE_MAX * DIMENSION_IMAGE_MAX


@dataclass(frozen=True)
class FichierValide:
    """Résultat d'une validation réussie."""

    extension: str
    mime: str
    taille: int
    sha256: str


def _types_autorises() -> dict[str, set[str]]:
    types = dict(TYPES_AUTORISES)
    if settings.METIER["UPLOAD_ALLOW_OFFICE"]:
        types.update(TYPES_OFFICE)
    return types


def _verifier_pdf(fichier: UploadedFile) -> None:
    """Rejette les PDF chiffrés ou embarquant du code actif."""
    fichier.seek(0)
    try:
        lecteur = PdfReader(fichier)
        if lecteur.is_encrypted:
            raise TypeFichierNonAutorise("Les PDF protégés par mot de passe ne sont pas acceptés.")
        racine = lecteur.trailer.get("/Root", {})
        for cle in ("/OpenAction", "/AA", "/JavaScript", "/JS"):
            if cle in racine or ("/Names" in racine and "/JavaScript" in racine["/Names"]):
                logger.warning("PDF avec contenu actif refusé (%s)", cle)
                raise TypeFichierNonAutorise("Les PDF contenant du code actif ne sont pas acceptés.")
    except TypeFichierNonAutorise:
        raise
    except Exception as exc:  # noqa: BLE001 – PDF corrompu / illisible
        raise TypeFichierNonAutorise("Le fichier PDF est illisible ou corrompu.") from exc
    finally:
        fichier.seek(0)


def _verifier_image(fichier: UploadedFile) -> None:
    """Vérifie l'intégrité de l'image et borne ses dimensions."""
    fichier.seek(0)
    try:
        with Image.open(fichier) as image:
            largeur, hauteur = image.size
            if largeur > DIMENSION_IMAGE_MAX or hauteur > DIMENSION_IMAGE_MAX:
                raise TypeFichierNonAutorise("L'image est trop grande (10 000 px maximum par côté).")
            image.verify()
    except TypeFichierNonAutorise:
        raise
    except Exception as exc:  # noqa: BLE001
        raise TypeFichierNonAutorise("Le fichier image est illisible ou corrompu.") from exc
    finally:
        fichier.seek(0)


def valider_fichier(fichier: UploadedFile) -> FichierValide:
    """Applique l'ensemble des contrôles et renvoie les métadonnées validées."""
    taille_max = settings.METIER["UPLOAD_MAX_BYTES"]
    if fichier.size is None or fichier.size == 0:
        raise TypeFichierNonAutorise("Le fichier est vide.")
    if fichier.size > taille_max:
        raise FichierTropVolumineux(
            f"Le fichier dépasse la taille maximale de {taille_max // (1024 * 1024)} Mo.",
            taille_max=taille_max,
        )

    types = _types_autorises()
    extension = Path(fichier.name or "").suffix.lower()
    if extension not in types:
        raise TypeFichierNonAutorise(
            f"Extension non autorisée. Formats acceptés : {', '.join(sorted(types))}.",
            extensions_autorisees=sorted(types),
        )

    mime_declare = (fichier.content_type or "").split(";")[0].strip().lower()
    if mime_declare and mime_declare not in types[extension]:
        raise TypeFichierNonAutorise("Le type déclaré ne correspond pas à l'extension du fichier.")

    fichier.seek(0)
    mime_reel = magic.from_buffer(fichier.read(8192), mime=True)
    fichier.seek(0)
    if mime_reel not in types[extension]:
        logger.warning("Upload refusé : extension %s mais contenu %s", extension, mime_reel)
        raise TypeFichierNonAutorise("Le contenu du fichier ne correspond pas à son extension.")

    if mime_reel == "application/pdf":
        _verifier_pdf(fichier)
    elif mime_reel.startswith("image/"):
        _verifier_image(fichier)

    empreinte = hashlib.sha256()
    for bloc in fichier.chunks():
        empreinte.update(bloc)
    fichier.seek(0)

    return FichierValide(extension=extension, mime=mime_reel, taille=fichier.size, sha256=empreinte.hexdigest())


def nettoyer_nom_original(nom: str | None) -> str:
    """Nettoie le nom d'origine (utilisé uniquement dans `Content-Disposition`)."""
    base = Path(nom or "fichier").name
    base = "".join(c for c in base if c.isprintable() and c not in '/\\:*?"<>|')
    return (base or "fichier")[:255]
