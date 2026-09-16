"""Utilitaires de formatage partagés (montants, dates) – utilisés par les PDF et les emails."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import Decimal

CARACTERES_CONTROLE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def format_montant(valeur: Decimal | int | float | None) -> str:
    """Formate un montant en euros à la française : `1 250 000,00`."""
    if valeur is None:
        return "—"
    montant = Decimal(valeur).quantize(Decimal("0.01"))
    entier, decimales = f"{montant:.2f}".split(".")
    signe = "-" if entier.startswith("-") else ""
    entier = entier.lstrip("-")
    groupes = []
    while entier:
        groupes.insert(0, entier[-3:])
        entier = entier[:-3]
    return f"{signe}{' '.join(groupes)},{decimales}"


def format_date(valeur: date | None) -> str:
    """Formate une date au format `jj/mm/aaaa`."""
    return valeur.strftime("%d/%m/%Y") if valeur else "—"


MOIS_FR = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]


def format_date_longue(valeur: date) -> str:
    """Formate une date en toutes lettres : `15 septembre 2026`."""
    return f"{valeur.day} {MOIS_FR[valeur.month - 1]} {valeur.year}"


def nettoyer_texte(valeur: str | None) -> str | None:
    """Supprime les caractères de contrôle et les espaces superflus d'une saisie."""
    if valeur is None:
        return None
    return CARACTERES_CONTROLE.sub("", valeur).strip()


def normaliser(texte: str) -> str:
    """
    Normalise un texte pour comparaison insensible à la casse et aux accents.

    Utilisé par l'analyse de cohérence : « SARL Dupont » et « sarl DUPONT » sont égaux.
    """
    sans_accents = unicodedata.normalize("NFKD", texte)
    sans_accents = "".join(c for c in sans_accents if not unicodedata.combining(c))
    sans_accents = re.sub(r"[^\w\s]", " ", sans_accents.casefold())
    return re.sub(r"\s+", " ", sans_accents).strip()
