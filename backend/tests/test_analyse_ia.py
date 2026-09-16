"""Contrôles unitaires de l'analyse de cohérence simulée."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from apps.attestations.services.analyse_ia import analyser


def fdr(**kw):
    base = dict(
        assure_nom="SARL DUPONT",
        assure_ville="Lyon",
        numero_contrat="RCD123456",
        chantier_nom="Halle Bouchayer",
        chantier_ville="Grenoble",
        date_debut=date(2026, 10, 1),
        date_fin=date(2027, 6, 30),
        cout_total=Decimal("1250000.00"),
        montant_prestation=Decimal("300000.00"),
        activite_couverte=True,
        type_intervention="ENTREPRISE_PRINCIPALE",
        description_travaux="Reprise de la charpente métallique et renforcement des poteaux existants.",
    )
    base.update(kw)
    return SimpleNamespace(**base)


CORPS_OK = """
<h1>Attestation d'assurance responsabilité civile décennale</h1>
<p>Assuré : SARL Dupont, Lyon, contrat n° RCD123456. Chantier Halle Bouchayer à Grenoble,
du 01/10/2026 au 30/06/2027. Coût total 1 250 000,00 € HT, prestation 300 000,00 € HT.
Travaux : reprise de la charpente métallique et renforcement des poteaux existants.</p>
<p>Elle ne peut engager l'assureur au-delà des clauses et conditions du contrat.</p>
"""


def codes(res):
    return {i.code for i in res.incoherences}


def test_coherent():
    res = analyser(fdr(), CORPS_OK, "PROJET")
    assert res.statut == "COHERENT" and res.score == 100 and not res.incoherences


def test_vide():
    res = analyser(fdr(), "<p></p>", "PROJET")
    assert res.statut == "INCOHERENT" and codes(res) == {"ATTESTATION_VIDE"}


def test_placeholder_et_chip_vide():
    res = analyser(fdr(), CORPS_OK + '<p>{{ signataire }}</p><span data-variable="x"></span>', "PROJET")
    assert "PLACEHOLDER_NON_REMPLI" in codes(res)


def test_assure_absent_et_montant_different():
    html = CORPS_OK.replace("SARL Dupont", "SAS MARTIN").replace("300 000,00 €", "450 000,00 €")
    res = analyser(fdr(), html, "PROJET")
    assert {"ASSURE_ABSENT", "MONTANT_DIFFERENT"} <= codes(res)
    montant = next(i for i in res.incoherences if i.code == "MONTANT_DIFFERENT")
    assert montant.extrait == "450 000,00 €" and montant.offset is not None


def test_dates_hors_fdr_et_invalide():
    res = analyser(fdr(), CORPS_OK.replace("30/06/2027", "31/02/2027"), "PROJET")
    assert "DATE_INVALIDE" in codes(res)
    res = analyser(fdr(), CORPS_OK.replace("30/06/2027", "30/06/2028"), "PROJET")
    assert "DATE_HORS_FDR" in codes(res)


def test_periode_inversee():
    res = analyser(
        fdr(date_debut=date(2027, 6, 30), date_fin=date(2026, 10, 1)),
        CORPS_OK.replace("du 01/10/2026 au 30/06/2027", "du 30/06/2027 au 01/10/2026"),
        "PROJET",
    )
    assert "PERIODE_INCOHERENTE" in codes(res)


def test_activite_hors_contrat_presentee_couverte():
    html = CORPS_OK + "<p>Les travaux relèvent des activités déclarées au contrat.</p>"
    res = analyser(fdr(activite_couverte=False), html, "PROJET")
    assert "ACTIVITE_HORS_CONTRAT" in codes(res) and res.statut == "INCOHERENT"


def test_definitive_mentionne_projet():
    res = analyser(fdr(), CORPS_OK + "<p>Ceci est un projet.</p>", "DEFINITIVE")
    assert "DEFINITIVE_MENTION_PROJET" in codes(res)
    assert "DEFINITIVE_MENTION_PROJET" not in codes(analyser(fdr(), CORPS_OK + "<p>Ceci est un projet.</p>", "PROJET"))


def test_travaux_absents_et_mentions():
    html = "<h1>Attestation décennale</h1><p>SARL Dupont Lyon RCD123456 Halle Bouchayer Grenoble du 01/10/2026 au 30/06/2027.</p>"
    res = analyser(fdr(), html, "PROJET")
    assert {"TRAVAUX_ABSENTS", "MENTION_RESERVE_ABSENTE"} <= codes(res)
    assert res.score == 80 and res.statut == "COHERENT"  # deux moyennes = 20 points, pas de majeure
