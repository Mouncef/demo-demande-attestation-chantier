"""Attestations : projet (distributeur), définitive (siège), analyse IA, validation, PDF."""

import pytest

from apps.notifications.models import Notification
from tests.conftest import creer_demande

pytestmark = pytest.mark.django_db


def base(demande, kind="projet"):
    return f"/api/v1/demandes/{demande.pk}/attestations/{kind}/"


def soumettre_projet(api_distributeur, demande, html=None):
    """Le distributeur enregistre (gabarit pré-rempli par défaut) et soumet son projet : prérequis de la définitive."""
    url = base(demande)
    html = html or api_distributeur.get(url + "gabarit/").json()["contenu_html"]
    assert api_distributeur.put(url, {"contenu_html": html}, format="json").status_code == 200
    assert api_distributeur.post(url + "soumettre/").status_code == 200
    return html


def test_gabarit_prerempli(api_distributeur, demande_brouillon):
    r = api_distributeur.get(base(demande_brouillon) + "gabarit/")
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "GABARIT" and 'data-variable="assure_nom"' in data["contenu_html"]
    assert data["variables"]["assure_nom"] == "SAS BÂTI-RHÔNE" and "assure_nom" in data["variables_disponibles"]


def test_projet_impossible_avant_acceptation(api_distributeur, demande_brouillon, demande_en_cours):
    """Le projet se prépare une fois la demande acceptée : 409 avant."""
    html = api_distributeur.get(base(demande_brouillon) + "gabarit/").json()["contenu_html"]
    for d in (demande_brouillon, demande_en_cours):
        r = api_distributeur.put(base(d), {"contenu_html": html}, format="json")
        assert r.status_code == 409, r.json()
        assert (
            "editer_projet_attestation"
            not in api_distributeur.get(f"/api/v1/demandes/{d.pk}/").json()["actions_possibles"]
        )


def test_projet_cycle_complet(
    api_distributeur, api_siege, demande_acceptee, siege, distributeur, django_capture_on_commit_callbacks
):
    from django.core import mail

    url = base(demande_acceptee)
    assert (
        "editer_projet_attestation"
        in api_distributeur.get(f"/api/v1/demandes/{demande_acceptee.pk}/").json()["actions_possibles"]
    )
    assert api_distributeur.get(url).status_code == 404
    html = api_distributeur.get(url + "gabarit/").json()["contenu_html"]
    html_malveillant = html + '<script>alert(1)</script><img src="x" onerror="alert(1)"><a href="http://evil">lien</a>'
    r = api_distributeur.put(url, {"contenu_html": html_malveillant, "contenu_json": {"type": "doc"}}, format="json")
    assert r.status_code == 200 and r.json()["statut"] == "EN_EDITION"
    stocke = r.json()["contenu_html"]
    assert "<script" not in stocke and "onerror" not in stocke and "<a " not in stocke and "data-variable" in stocke
    # Le siège lit mais n'édite pas le projet ; il ne peut ni le soumettre ni le valider
    assert api_siege.get(url).status_code == 200
    assert api_siege.put(url, {"contenu_html": html}, format="json").status_code == 403
    assert api_siege.post(url + "soumettre/").status_code == 403
    assert api_distributeur.post(url + "valider/", {}, format="json").status_code == 409
    # Prévisualisation et PDF à la volée
    r = api_distributeur.post(url + "previsualiser/", {}, format="json")
    assert r.status_code == 200 and b"PROJET" in r.content and b"AXA France IARD" in r.content
    r = api_distributeur.get(url + "pdf/")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"

    # Soumission au siège : statut SOUMISE, notification + email au siège, projet figé pour l'agent
    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        r = api_distributeur.post(url + "soumettre/")
    assert r.status_code == 200 and r.json()["statut"] == "SOUMISE" and r.json()["soumise_le"]
    assert Notification.objects.filter(destinataire=siege, type="PROJET_ATTESTATION_SOUMIS").exists()
    assert (
        len(mail.outbox) == 1 and siege.email in mail.outbox[0].to and "Projet d'attestation" in mail.outbox[0].subject
    )
    assert api_distributeur.put(url, {"contenu_html": html}, format="json").status_code == 409
    assert api_distributeur.post(url + "soumettre/").status_code == 409
    detail = api_siege.get(f"/api/v1/demandes/{demande_acceptee.pk}/").json()
    assert detail["etat_attestation"] == "PROJET_SOUMIS" and "traiter_projet_attestation" in detail["actions_possibles"]
    assert api_siege.get("/api/v1/demandes/", {"projet_soumis": "true"}).json()["count"] == 1

    # Le siège renvoie le projet pour correction : notification + email à l'agent, qui corrige et resoumet
    assert (
        api_distributeur.post(
            url + "demander-correction/", {"commentaire": "Merci de corriger la ville."}, format="json"
        ).status_code
        == 403
    )
    assert api_siege.post(url + "demander-correction/", {"commentaire": "court"}, format="json").status_code == 400
    with django_capture_on_commit_callbacks(execute=True):
        r = api_siege.post(
            url + "demander-correction/", {"commentaire": "Merci de corriger la ville du chantier."}, format="json"
        )
    assert r.status_code == 200 and r.json()["statut"] == "A_CORRIGER" and "ville" in r.json()["commentaire_siege"]
    assert Notification.objects.filter(destinataire=distributeur, type="PROJET_ATTESTATION_A_CORRIGER").exists()
    assert (
        api_distributeur.get(f"/api/v1/demandes/{demande_acceptee.pk}/").json()["etat_attestation"]
        == "PROJET_A_CORRIGER"
    )
    assert api_distributeur.put(url, {"contenu_html": html}, format="json").status_code == 200
    assert api_distributeur.post(url + "soumettre/").json()["statut"] == "SOUMISE"
    # Reprise volontaire par l'agent puis nouvelle soumission
    assert api_distributeur.post(url + "rouvrir/").json()["statut"] == "EN_EDITION"
    assert api_distributeur.post(url + "soumettre/").json()["statut"] == "SOUMISE"
    historique = [h["action"] for h in api_siege.get(f"/api/v1/demandes/{demande_acceptee.pk}/historique/").json()]
    assert historique.count("ATTESTATION_PROJET_SOUMISE") == 3 and "ATTESTATION_PROJET_A_CORRIGER" in historique


def test_definitive_invisible_pour_le_distributeur_avant_validation(api_distributeur, api_siege, demande_acceptee):
    soumettre_projet(api_distributeur, demande_acceptee)
    url = base(demande_acceptee, "definitive")
    html = api_siege.get(url + "gabarit/").json()["contenu_html"]
    api_siege.put(url, {"contenu_html": html}, format="json")
    assert api_distributeur.get(url).status_code == 404
    assert api_distributeur.get(url + "pdf/").status_code == 404
    assert (
        api_distributeur.get(f"/api/v1/demandes/{demande_acceptee.pk}/").json()["etat_attestation"] == "PROJET_SOUMIS"
    )


def test_definitive_prerempli_depuis_projet_soumis_et_projet_fige(api_distributeur, api_siege, demande_acceptee):
    projet = base(demande_acceptee)
    html = (
        api_distributeur.get(projet + "gabarit/")
        .json()["contenu_html"]
        .replace("</h1>", "</h1><p>Mention ajoutée par l'agent.</p>")
    )
    api_distributeur.put(projet, {"contenu_html": html}, format="json")
    # Non soumis : le siège ne peut ni consulter le gabarit ni établir la définitive, et n'a pas l'action
    assert api_siege.get(base(demande_acceptee, "definitive") + "gabarit/").status_code == 409
    assert api_siege.put(base(demande_acceptee, "definitive"), {"contenu_html": html}, format="json").status_code == 409
    actions = api_siege.get(f"/api/v1/demandes/{demande_acceptee.pk}/").json()["actions_possibles"]
    assert "editer_attestation_definitive" not in actions and "traiter_projet_attestation" not in actions
    api_distributeur.post(projet + "soumettre/")
    actions = api_siege.get(f"/api/v1/demandes/{demande_acceptee.pk}/").json()["actions_possibles"]
    assert {"editer_attestation_definitive", "traiter_projet_attestation"} <= set(actions)
    g = api_siege.get(base(demande_acceptee, "definitive") + "gabarit/").json()
    assert g["source"] == "PROJET" and "Mention ajoutée par l'agent" in g["contenu_html"] and g["projet_soumis_le"]
    # Le siège établit et valide la définitive : l'agent la voit, le projet est figé
    url = base(demande_acceptee, "definitive")
    api_siege.put(url, {"contenu_html": g["contenu_html"]}, format="json")
    assert api_siege.post(url + "analyser/").json()["statut"] == "COHERENT"
    assert api_siege.post(url + "valider/", {}, format="json").status_code == 200
    assert api_distributeur.get(url).status_code == 200
    assert api_distributeur.get(url + "pdf/").status_code == 200
    detail = api_distributeur.get(f"/api/v1/demandes/{demande_acceptee.pk}/").json()
    assert (
        detail["etat_attestation"] == "DEFINITIVE"
        and "telecharger_attestation_definitive" in detail["actions_possibles"]
    )
    assert "editer_projet_attestation" not in detail["actions_possibles"]
    assert api_distributeur.post(projet + "rouvrir/").status_code == 409
    assert (
        api_siege.post(
            projet + "demander-correction/", {"commentaire": "Trop tard pour corriger."}, format="json"
        ).status_code
        == 409
    )


def test_definitive_reservee_au_siege_et_a_l_acceptation(
    api_distributeur, api_siege, demande_en_cours, demande_acceptee
):
    soumettre_projet(api_distributeur, demande_acceptee)
    html = api_siege.get(base(demande_acceptee, "definitive") + "gabarit/").json()["contenu_html"]
    assert (
        api_distributeur.put(base(demande_acceptee, "definitive"), {"contenu_html": html}, format="json").status_code
        == 403
    )
    assert api_siege.put(base(demande_en_cours, "definitive"), {"contenu_html": html}, format="json").status_code == 409
    assert api_siege.put(base(demande_acceptee, "definitive"), {"contenu_html": html}, format="json").status_code == 200


def test_definitive_refusee_impossible(api_siege, distributeur, siege):
    from apps.demandes.services import workflow

    d = creer_demande(distributeur)
    workflow.envoyer(d.pk, distributeur)
    workflow.refuser(d.pk, siege, "Motif de refus suffisant.")
    r = api_siege.put(base(d, "definitive"), {"contenu_html": "<p>x</p>"}, format="json")
    assert r.status_code == 409 and r.json()["decision"] == "REFUSEE"


def test_definitive_validation_exige_analyse_coherente(api_siege, api_distributeur, demande_acceptee, distributeur):
    soumettre_projet(api_distributeur, demande_acceptee)
    url = base(demande_acceptee, "definitive")
    html = api_siege.get(url + "gabarit/").json()["contenu_html"]
    # Contenu incohérent : mention d'une garantie hors périmètre + autre n° de contrat
    incoherent = html.replace("</h1>", "</h1><p>Inclut la garantie dommages-ouvrage. Contrat n° ZZZ999999.</p>")
    api_siege.put(url, {"contenu_html": incoherent}, format="json")
    # Sans analyse → 409
    r = api_siege.post(url + "valider/", {}, format="json")
    assert r.status_code == 409 and r.json()["code"] == "ANALYSE_INCOHERENTE"
    r = api_siege.post(url + "analyser/")
    assert r.json()["statut"] == "INCOHERENT"
    codes = {i["code"] for i in r.json()["resultat"]["incoherences"]}
    assert {"GARANTIE_NON_DECLAREE", "CONTRAT_DIFFERENT"} <= codes
    assert any(i["extrait"] and i["offset"] is not None for i in r.json()["resultat"]["incoherences"])
    # Analyse incohérente → toujours 409 ; forçage sans justification → 409 ; avec justification → OK
    assert api_siege.post(url + "valider/", {}, format="json").status_code == 409
    assert (
        api_siege.post(url + "valider/", {"forcer": True, "justification": "court"}, format="json").status_code == 409
    )
    # Correction du contenu puis analyse cohérente → validation normale
    api_siege.put(url, {"contenu_html": html}, format="json")
    assert api_siege.post(url + "valider/", {}, format="json").status_code == 409  # analyse périmée (hash différent)
    assert api_siege.post(url + "analyser/").json()["statut"] == "COHERENT"
    assert api_siege.get(url).json()["analyse_a_jour"] is True
    r = api_siege.post(url + "valider/", {}, format="json")
    assert r.status_code == 200 and r.json()["numero"].startswith("ATT-") and r.json()["statut"] == "VALIDEE"
    assert Notification.objects.filter(destinataire=distributeur, type="ATTESTATION_DISPONIBLE").exists()
    # PDF accessible au distributeur, contenu immuable, pas de réouverture
    r = api_distributeur.get(url + "pdf/")
    assert r.status_code == 200 and b"".join(r.streaming_content)[:4] == b"%PDF"
    assert api_siege.put(url, {"contenu_html": html}, format="json").status_code == 409
    assert api_siege.post(url + "rouvrir/").status_code == 409
    # Le distributeur n'analyse pas la définitive et ne voit ni l'historique ni le résultat des analyses
    assert api_distributeur.post(url + "analyser/").status_code == 403
    assert api_distributeur.get(url + "analyses/").status_code == 403
    assert api_distributeur.get(url).json()["derniere_analyse"] is None
    assert api_siege.get(url).json()["derniere_analyse"]["statut"] == "COHERENT"


def test_pdf_projet_sans_enregistrement(api_distributeur, api_siege, demande_acceptee):
    """Un projet jamais enregistré s'exporte quand même (gabarit pré-rempli), y compris en lecture seule."""
    r = api_distributeur.get(base(demande_acceptee) + "pdf/")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    assert api_siege.get(base(demande_acceptee) + "pdf/").status_code == 200
    # Prévisualisation du contenu fourni sans enregistrement préalable
    r = api_siege.post(
        base(demande_acceptee) + "previsualiser/", {"contenu_html": "<h1>Aperçu test</h1>"}, format="json"
    )
    assert r.status_code == 200 and b"Aper\xc3\xa7u test" in r.content


def test_pdf_definitive_non_validee_404(api_siege, api_distributeur, demande_acceptee):
    soumettre_projet(api_distributeur, demande_acceptee)
    url = base(demande_acceptee, "definitive")
    api_siege.put(url, {"contenu_html": "<p>brouillon</p>"}, format="json")
    assert api_siege.get(url + "pdf/").status_code == 404


def test_gabarit_format_officiel_axa(api_siege, api_distributeur, demande_acceptee):
    """Le gabarit reprend la structure du modèle AXA (titre, assuré + SIRET, contrat, sections, tableau, signature)."""
    soumettre_projet(api_distributeur, demande_acceptee)
    r = api_siege.get(base(demande_acceptee, "definitive") + "gabarit/")
    assert r.status_code == 200
    data = r.json()
    html = data["contenu_html"]
    for attendu in (
        "ATTESTATION D’ASSURANCE",
        "833 207 194 00014",
        "BTPlus Concept",
        "1- Les garanties objet de la présente attestation",
        "2- La garantie de responsabilité décennale obligatoire",
        "3- Autres garanties souscrites",
        'class="section-droite">Activités Garanties',
        'class="garanties"',
        "Franchise par sinistre",
        "Directeur Général Délégué",
    ):
        assert attendu in html, attendu
    v = data["variables"]
    assert v["assure_cp_ville"] == "69002 Lyon" and v["produit"] == "BTPlus Concept"
    assert v["contrat_periode_debut"].startswith("01/01/") and v["contrat_periode_fin"].startswith("01/01/")
    entete = data["entete"]
    assert entete["destinataire"]["nom"] == "SAS BÂTI-RHÔNE" and entete["numero_contrat"] == "RCD2026LY0142"
    assert entete["intermediaire"]["email"] == demande_acceptee.distributeur.email
    assert "AXA France IARD" in entete["mentions_legales"]


def test_analyse_du_gabarit_intact_coherente(api_siege, api_distributeur, demande_acceptee):
    """Le gabarit officiel enregistré tel quel (tableau de garanties, période du contrat) est COHÉRENT."""
    soumettre_projet(api_distributeur, demande_acceptee)
    url = base(demande_acceptee, "definitive")
    html = api_siege.get(url + "gabarit/").json()["contenu_html"]
    assert api_siege.put(url, {"contenu_html": html}, format="json").status_code == 200
    r = api_siege.post(url + "analyser/")
    assert r.status_code == 201, r.json()
    resultat = r.json()["resultat"]
    assert resultat["statut"] == "COHERENT", resultat["incoherences"]
    assert {"SIRET_ABSENT", "MONTANT_DIFFERENT", "DATE_HORS_FDR", "GARANTIE_NON_DECLAREE"} <= set(
        resultat["controles_ok"]
    ), resultat["incoherences"]
    # Les classes de mise en page du format (sections, tableau) survivent à la sanitisation.
    stocke = api_siege.get(url).json()["contenu_html"]
    assert 'class="section-droite"' in stocke and 'class="garanties"' in stocke
    # Le PDF de prévisualisation porte le cadre officiel.
    r = api_siege.post(url + "previsualiser/", {"contenu_html": html}, format="json")
    assert b"Votre Interm" in r.content and b"Date du courrier" in r.content and b"Vos r" in r.content


def test_apercu_pdf_identique_a_l_export(api_distributeur, demande_acceptee):
    """L'aperçu en PDF est produit par le même moteur que l'export ; le gabarit expose la feuille de style."""
    url = base(demande_acceptee)
    gabarit = api_distributeur.get(url + "gabarit/").json()
    assert "@page" in gabarit["css_document"] and "table.garanties" in gabarit["css_document"]
    r = api_distributeur.post(
        url + "previsualiser/?sortie=pdf", {"contenu_html": gabarit["contenu_html"]}, format="json"
    )
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf" and r.content.startswith(b"%PDF")
    assert r["Content-Disposition"].startswith("inline")
    r = api_distributeur.post(url + "previsualiser/", {"contenu_html": gabarit["contenu_html"]}, format="json")
    assert r.status_code == 200 and b'class="document"' in r.content and b"Votre Interm" in r.content
