"""
Catalogue des types de pièces justificatives.

Le catalogue est la référence unique partagée par :
  * la migration de données qui alimente la table `TypePiece` ;
  * le service `apps.demandes.services.exigences` qui détermine les pièces requises ;
  * le référentiel exposé au frontend (`GET /referentiels/`).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DefinitionTypePiece:
    code: str
    libelle: str
    description: str
    ordre: int


# Codes (constantes utilisées par les règles métier)
ETUDE_STRUCTURE = "ETUDE_STRUCTURE"
AUTORISATION_URBANISME = "AUTORISATION_URBANISME"
DESCRIPTIF_TECHNIQUE = "DESCRIPTIF_TECHNIQUE"
PHOTOS_PLANS = "PHOTOS_PLANS"
MARCHE_SIGNE = "MARCHE_SIGNE"
ATTESTATION_DO = "ATTESTATION_DO"
PLANNING_PREVISIONNEL = "PLANNING_PREVISIONNEL"
DESCRIPTIF_ACTIVITE = "DESCRIPTIF_ACTIVITE"
JUSTIFICATIF_QUALIFICATION = "JUSTIFICATIF_QUALIFICATION"
AVIS_TECHNIQUE = "AVIS_TECHNIQUE"
CONTRAT_SOUS_TRAITANCE = "CONTRAT_SOUS_TRAITANCE"
AUTRE = "AUTRE"

CATALOGUE: tuple[DefinitionTypePiece, ...] = (
    DefinitionTypePiece(
        ETUDE_STRUCTURE,
        "Étude ou note de calcul structure (BET)",
        "Étude réalisée par un bureau d'études techniques justifiant la modification de structure.",
        10,
    ),
    DefinitionTypePiece(
        AUTORISATION_URBANISME,
        "Permis de construire ou déclaration préalable",
        "Autorisation d'urbanisme couvrant les travaux touchant à la structure.",
        20,
    ),
    DefinitionTypePiece(
        DESCRIPTIF_TECHNIQUE,
        "Descriptif technique détaillé du chantier",
        "Description des techniques, matériaux et procédés mis en œuvre sur un chantier atypique.",
        30,
    ),
    DefinitionTypePiece(
        PHOTOS_PLANS, "Photos du site et/ou plans", "Photographies de l'existant et plans du projet.", 40
    ),
    DefinitionTypePiece(
        MARCHE_SIGNE, "Devis accepté ou marché signé", "Document contractuel justifiant le montant de l'opération.", 50
    ),
    DefinitionTypePiece(
        ATTESTATION_DO,
        "Attestation d'assurance dommages-ouvrage",
        "Attestation DO souscrite par le maître d'ouvrage (obligatoire au-delà de certains seuils).",
        60,
    ),
    DefinitionTypePiece(
        PLANNING_PREVISIONNEL, "Planning prévisionnel des travaux", "Calendrier des phases du chantier.", 70
    ),
    DefinitionTypePiece(
        DESCRIPTIF_ACTIVITE,
        "Descriptif de l'activité hors contrat",
        "Description précise de l'activité non déclarée au contrat pour laquelle une extension est étudiée.",
        80,
    ),
    DefinitionTypePiece(
        JUSTIFICATIF_QUALIFICATION,
        "Justificatif de qualification",
        "Certification ou qualification professionnelle (Qualibat, RGE, QualiPV…).",
        90,
    ),
    DefinitionTypePiece(
        AVIS_TECHNIQUE,
        "Avis technique / ATEx / fiche procédé",
        "Justificatif pour un procédé ou des travaux non traditionnels (non couverts par les DTU).",
        100,
    ),
    DefinitionTypePiece(
        CONTRAT_SOUS_TRAITANCE,
        "Contrat de sous-traitance",
        "Contrat ou bon de commande liant le sous-traitant à l'entreprise principale.",
        110,
    ),
    DefinitionTypePiece(AUTRE, "Autre document", "Tout autre document utile à l'instruction.", 999),
)

CODES_CATALOGUE: frozenset[str] = frozenset(d.code for d in CATALOGUE)
LIBELLES: dict[str, str] = {d.code: d.libelle for d in CATALOGUE}
