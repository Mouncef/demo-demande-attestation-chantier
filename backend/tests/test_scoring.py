"""Grille de scoring simulée : points, niveaux et planchers."""

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

from apps.demandes.services.scoring import calculer_scoring


def fdr(**kw):
    base = dict(
        cout_total=Decimal("100000"),
        montant_prestation=Decimal("50000"),
        type_intervention="ENTREPRISE_PRINCIPALE",
        type_chantier="CONSTRUCTION_NEUVE",
        modification_structure=None,
        chantier_atypique=False,
        activite_couverte=True,
        travaux_standards=True,
        date_debut=date.today(),
        date_fin=date.today() + timedelta(days=60),
        usage="BUREAU",
        numero_contrat=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_faible_par_defaut():
    s = calculer_scoring(fdr(), [])
    assert s.niveau == "FAIBLE" and s.points == 0 and "FAIBLE" in s.synthese


def test_gros_chantier_structure_eleve():
    s = calculer_scoring(
        fdr(
            cout_total=Decimal("12000000"),
            montant_prestation=Decimal("2000000"),
            type_chantier="RENOVATION",
            modification_structure=True,
        ),
        [],
    )
    assert s.points >= 65 and s.niveau == "ELEVE"
    assert {i.code for i in s.indicateurs} >= {
        "MONTANT",
        "RENOVATION_STRUCTURE",
        "MONTANT_PRESTATION",
        "DOSSIER_INCOMPLET",
    }


def test_plancher_hors_contrat_modere():
    s = calculer_scoring(fdr(activite_couverte=False), [])
    # 30 (hors contrat) + 10 (dossier incomplet) = 40 → MODERE naturellement ; le plancher n'est pas nécessaire
    assert s.niveau == "MODERE"


def test_plancher_hors_contrat_atypique_eleve():
    s = calculer_scoring(fdr(activite_couverte=False, chantier_atypique=True), [])
    assert s.niveau == "ELEVE" and s.planchers


def test_score_borne_a_100():
    s = calculer_scoring(
        fdr(
            cout_total=Decimal("20000000"),
            montant_prestation=Decimal("19000000"),
            type_intervention="SOUS_TRAITANT",
            type_chantier="RENOVATION",
            modification_structure=True,
            chantier_atypique=True,
            activite_couverte=False,
            travaux_standards=False,
            date_fin=date.today() + timedelta(days=2000),
            usage="AUTRE",
            numero_contrat="ABC123456",
        ),
        [],
    )
    assert s.score == 100 and s.points > 100
