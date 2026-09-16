"""Règles de pièces requises et complétude (fonctions pures)."""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from apps.demandes.services.exigences import Niveau, calculer_completude, calculer_exigences
from apps.pieces import catalogue


def fdr(**kw):
    base = dict(
        modification_structure=None,
        chantier_atypique=False,
        cout_total=None,
        activite_couverte=True,
        travaux_standards=True,
        type_intervention="ENTREPRISE_PRINCIPALE",
    )
    base.update(kw)
    return SimpleNamespace(**base)


def codes(f):
    return [e.code for e in calculer_exigences(f)]


def test_aucune_piece_par_defaut():
    assert codes(fdr()) == []


def test_structure_declenche_etude_et_urbanisme():
    assert codes(fdr(modification_structure=True)) == [catalogue.ETUDE_STRUCTURE, catalogue.AUTORISATION_URBANISME]


def test_atypique():
    assert codes(fdr(chantier_atypique=True)) == [catalogue.DESCRIPTIF_TECHNIQUE, catalogue.PHOTOS_PLANS]


@pytest.mark.parametrize(
    "montant,attendu",
    [
        (Decimal("10000000.00"), False),  # seuil exact : rien
        (Decimal("10000000.01"), True),  # strictement supérieur
        (Decimal("9999999.99"), False),
    ],
)
def test_seuil_10M_strict(montant, attendu):
    assert (catalogue.MARCHE_SIGNE in codes(fdr(cout_total=montant))) is attendu


def test_hors_contrat_et_non_standard():
    assert codes(fdr(activite_couverte=False, travaux_standards=False)) == [
        catalogue.DESCRIPTIF_ACTIVITE,
        catalogue.JUSTIFICATIF_QUALIFICATION,
        catalogue.AVIS_TECHNIQUE,
    ]


def test_sous_traitance_recommandee_seulement():
    exigences = calculer_exigences(fdr(type_intervention="SOUS_TRAITANT"))
    assert [e.niveau for e in exigences] == [Niveau.RECOMMANDE]


def test_completude_ignore_recommandees_et_classe_hors_exigence():
    f = fdr(modification_structure=True, type_intervention="SOUS_TRAITANT")
    piece = SimpleNamespace(
        id="p1", nom_original="etude.pdf", type_piece_id=catalogue.ETUDE_STRUCTURE, taille=10, created_at=None
    )
    hors = SimpleNamespace(
        id="p2", nom_original="photo.png", type_piece_id=catalogue.PHOTOS_PLANS, taille=10, created_at=None
    )
    c = calculer_completude(f, [piece, hors])
    assert c.complet is False
    assert c.manquants == [catalogue.AUTORISATION_URBANISME]
    assert [p["id"] for p in c.pieces_hors_exigence] == ["p2"]
    urbanisme = SimpleNamespace(
        id="p3", nom_original="pc.pdf", type_piece_id=catalogue.AUTORISATION_URBANISME, taille=10, created_at=None
    )
    assert calculer_completude(f, [piece, urbanisme]).complet is True
