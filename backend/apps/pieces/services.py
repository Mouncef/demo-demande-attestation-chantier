"""Nommage des pièces jointes d'après le libellé de leur type."""

from __future__ import annotations

from apps.pieces.catalogue import LIBELLES

from .models import PieceJointe, TypePiece

CARACTERES_INTERDITS = '/\\:*?"<>|'


def nom_pour_type(demande_id, type_piece: TypePiece, extension: str, exclure: PieceJointe | None = None) -> str:
    """
    Nom de la pièce = libellé du type + extension ; « (n) » est ajouté si des pièces actives du
    même type existent déjà sur la demande (ex. « Photos du site et/ou plans (2).png »).
    """
    libelle = LIBELLES.get(type_piece.code, type_piece.libelle)
    base = "".join(c for c in libelle if c not in CARACTERES_INTERDITS).strip()
    existantes = PieceJointe.objects.actives().filter(demande_id=demande_id, type_piece=type_piece)
    if exclure is not None:
        existantes = existantes.exclude(pk=exclure.pk)
    nb = existantes.count()
    suffixe = f" ({nb + 1})" if nb else ""
    return f"{base}{suffixe}{extension.lower()}"[:255]
