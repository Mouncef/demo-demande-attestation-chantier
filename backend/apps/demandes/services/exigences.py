"""
Détermination des pièces justificatives requises et de la complétude du dossier.

Règles du sujet – une demande nécessite des pièces si :
  * rénovation avec modification de structure ;
  * usage « Autre » (→ précision textuelle obligatoire, traitée par la validation du FDR) ;
  * chantier atypique ;
  * montant global strictement supérieur à 10 M€ ;
  * activité hors contrat ;
  * travaux non standards.

Le calcul est déterministe : une liste ordonnée de règles `(prédicat, codes de pièces, raison)`
est parcourue ; chaque règle vraie ajoute ses pièces. Les fonctions acceptent tout objet
exposant les attributs du FDR (instance du modèle ou objet de test).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from django.conf import settings

from apps.pieces import catalogue
from apps.pieces.catalogue import LIBELLES

from ..choices import TypeIntervention


class Niveau:
    REQUIS = "REQUIS"
    RECOMMANDE = "RECOMMANDE"


@dataclass(frozen=True)
class Exigence:
    """Une pièce attendue, son niveau d'obligation et la raison métier."""

    code: str
    niveau: str
    raison: str

    @property
    def libelle(self) -> str:
        return LIBELLES.get(self.code, self.code)


@dataclass(frozen=True)
class Regle:
    predicat: Callable[[Any], bool]
    codes: tuple[str, ...]
    raison: str
    niveau: str = Niveau.REQUIS


def seuil_gros_chantier() -> Decimal:
    return Decimal(settings.METIER["SEUIL_GROS_CHANTIER"])


def _est_gros_chantier(fdr: Any) -> bool:
    """Coût total STRICTEMENT supérieur au seuil (10 000 000,00 € exactement ne déclenche rien)."""
    return fdr.cout_total is not None and Decimal(fdr.cout_total) > seuil_gros_chantier()


REGLES: tuple[Regle, ...] = (
    Regle(
        predicat=lambda f: f.modification_structure is True,
        codes=(catalogue.ETUDE_STRUCTURE, catalogue.AUTORISATION_URBANISME),
        raison="Rénovation avec modification de la structure",
    ),
    Regle(
        predicat=lambda f: f.chantier_atypique is True,
        codes=(catalogue.DESCRIPTIF_TECHNIQUE, catalogue.PHOTOS_PLANS),
        raison="Chantier atypique",
    ),
    Regle(
        predicat=_est_gros_chantier,
        codes=(catalogue.MARCHE_SIGNE, catalogue.ATTESTATION_DO, catalogue.PLANNING_PREVISIONNEL),
        raison="Coût total du chantier supérieur à 10 M€",
    ),
    Regle(
        predicat=lambda f: f.activite_couverte is False,
        codes=(catalogue.DESCRIPTIF_ACTIVITE, catalogue.JUSTIFICATIF_QUALIFICATION),
        raison="Activité non couverte par le contrat",
    ),
    Regle(
        predicat=lambda f: f.travaux_standards is False,
        codes=(catalogue.AVIS_TECHNIQUE,),
        raison="Travaux non standards (procédé non traditionnel)",
    ),
    Regle(
        predicat=lambda f: f.type_intervention == TypeIntervention.SOUS_TRAITANT,
        codes=(catalogue.CONTRAT_SOUS_TRAITANCE,),
        raison="Intervention en sous-traitance",
        niveau=Niveau.RECOMMANDE,
    ),
)


def calculer_exigences(fdr: Any) -> list[Exigence]:
    """Renvoie la liste ordonnée et dédoublonnée des pièces attendues pour ce FDR."""
    exigences: list[Exigence] = []
    vus: set[str] = set()
    for regle in REGLES:
        if not regle.predicat(fdr):
            continue
        for code in regle.codes:
            if code in vus:
                continue
            vus.add(code)
            exigences.append(Exigence(code=code, niveau=regle.niveau, raison=regle.raison))
    return exigences


@dataclass
class EtatExigence:
    """Exigence enrichie des pièces fournies."""

    code: str
    libelle: str
    niveau: str
    raison: str
    satisfait: bool
    pieces: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Completude:
    """Résultat du contrôle de complétude documentaire."""

    complet: bool
    exigences: list[EtatExigence]
    pieces_hors_exigence: list[dict[str, Any]]
    manquants: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "complet": self.complet,
            "exigences": [e.__dict__ for e in self.exigences],
            "pieces_hors_exigence": self.pieces_hors_exigence,
            "manquants": self.manquants,
        }


def _resume_piece(piece: Any) -> dict[str, Any]:
    return {
        "id": str(piece.id),
        "nom_fichier": getattr(piece, "nom_fichier", None) or piece.nom_original,
        "nom_original": piece.nom_original,
        "type_piece": piece.type_piece_id,
        "taille": piece.taille,
        "created_at": piece.created_at.isoformat() if piece.created_at else None,
    }


def calculer_completude(fdr: Any, pieces: Iterable[Any]) -> Completude:
    """
    Dossier complet ⇔ chaque exigence REQUISE a au moins une pièce (non supprimée) de ce type.

    Les pièces dont le type n'est plus exigé (le FDR a changé après l'upload) ne sont jamais
    supprimées automatiquement : elles sont renvoyées dans `pieces_hors_exigence` avec le
    statut « facultative ».
    """
    exigences = calculer_exigences(fdr)
    codes_exiges = {e.code for e in exigences}
    pieces_par_code: dict[str, list[dict[str, Any]]] = {}
    hors_exigence: list[dict[str, Any]] = []
    for piece in pieces:
        resume = _resume_piece(piece)
        if piece.type_piece_id in codes_exiges:
            pieces_par_code.setdefault(piece.type_piece_id, []).append(resume)
        else:
            hors_exigence.append(
                {
                    **resume,
                    "libelle": LIBELLES.get(piece.type_piece_id, piece.type_piece_id),
                    "info": "Ce type de pièce n'est pas (ou plus) requis pour ce dossier : pièce facultative.",
                }
            )

    etats = [
        EtatExigence(
            code=e.code,
            libelle=e.libelle,
            niveau=e.niveau,
            raison=e.raison,
            satisfait=bool(pieces_par_code.get(e.code)),
            pieces=pieces_par_code.get(e.code, []),
        )
        for e in exigences
    ]
    manquants = [e.code for e in etats if e.niveau == Niveau.REQUIS and not e.satisfait]
    return Completude(complet=not manquants, exigences=etats, pieces_hors_exigence=hors_exigence, manquants=manquants)
