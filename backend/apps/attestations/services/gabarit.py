"""
Gabarit d'attestation AXA : variables injectées depuis le FDR et corps HTML initial.

Le document suit le format officiel AXA France (modèle « attestation-assurance-chantier.pdf ») :
  * un cadre non modifiable (en-tête « Votre Intermédiaire » / accroche / logo, étiquettes « Votre contrat »
    et « Vos références », destinataire, date du courrier, mentions légales, en-tête courant des pages
    suivantes et pagination) rendu par `templates/pdf/attestation.html` et reproduit dans l'éditeur ;
  * un corps éditable (TipTap) : titre, paragraphe d'attestation, chantier concerné, sections 1 à 3,
    « Activités Garanties », « Tableau de garanties », réserve et signature.

Le corps contient des « chips » `<span data-variable="cle">valeur</span>` dont les valeurs sont
rafraîchies depuis les variables à chaque rendu (prévisualisation, PDF, analyse) afin de rester
alignées sur le FDR ; le texte libre reste sous la responsabilité de l'utilisateur et est contrôlé
par l'analyse de cohérence.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from bs4 import BeautifulSoup
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from apps.comptes.models import User
from apps.core.utils import format_date, format_date_longue, format_montant
from apps.demandes.choices import TypeChantier, TypeIntervention, Usage
from apps.demandes.models import Demande
from apps.documents.logo import LOGO_AXA_DATA_URI

from ..models import Attestation, KindAttestation

# Libellés des variables proposées dans l'éditeur (panneau d'insertion).
VARIABLES_DISPONIBLES: dict[str, str] = {
    "assure_nom": "Nom / raison sociale de l'assuré",
    "assure_adresse": "Adresse de l'assuré",
    "assure_cp_ville": "Code postal et ville de l'assuré",
    "assure_ville": "Ville de l'assuré",
    "assure_siret": "SIRET de l'assuré",
    "numero_contrat": "Numéro de contrat",
    "reference_client": "Référence client",
    "produit": "Produit d'assurance (contrat)",
    "contrat_periode_debut": "Début de la période de validité du contrat",
    "contrat_periode_fin": "Fin de la période de validité du contrat",
    "plafond_cout": "Plafond du coût total de construction",
    "chantier_nom": "Nom du chantier",
    "chantier_ville": "Ville du chantier",
    "type_chantier": "Nature du chantier",
    "usage": "Destination de l'ouvrage",
    "date_debut": "Date de début du chantier",
    "date_fin": "Date de fin du chantier",
    "cout_total": "Coût total du chantier",
    "montant_prestation": "Montant de la prestation",
    "type_intervention": "Type d'intervention",
    "description_travaux": "Description des travaux",
    "activites_garanties": "Mention sur les activités garanties",
    "intermediaire_nom": "Intermédiaire (agence / cabinet)",
    "intermediaire_telephone": "Téléphone de l'intermédiaire",
    "intermediaire_email": "Email de l'intermédiaire",
    "distributeur_nom": "Distributeur émetteur",
    "numero_attestation": "Numéro d'attestation",
    "date_courrier": "Date du courrier",
    "date_edition": "Date d'édition (en toutes lettres)",
    "lieu_signature": "Lieu de signature",
    "signataire_nom": "Signataire",
    "signataire_titre": "Titre du signataire",
}


def periode_contrat(reference: date) -> tuple[date, date]:
    """
    Période de validité du contrat imprimée sur l'attestation : année civile de la date d'édition
    (du 1er janvier au 1er janvier suivant, comme sur le modèle AXA). Rectifiable dans l'éditeur.
    """
    return date(reference.year, 1, 1), date(reference.year + 1, 1, 1)


def calculer_variables(
    demande: Demande, kind: str, attestation: Attestation | None = None, signataire: User | None = None
) -> dict[str, Any]:
    """Valeurs des variables à partir du FDR, du profil de l'intermédiaire, du paramétrage et du contexte."""
    fdr = demande.fdr
    distributeur = demande.distributeur
    format_attestation = settings.METIER["ATTESTATION"]
    usage = fdr.get_usage_display() if fdr.usage else ""
    if fdr.usage == Usage.AUTRE and fdr.usage_autre_precision:
        usage = f"Autre : {fdr.usage_autre_precision}"
    nature = fdr.get_type_chantier_display() if fdr.type_chantier else ""
    if fdr.type_chantier == TypeChantier.RENOVATION and fdr.modification_structure:
        nature += " avec modification de structure"
    intervention = fdr.get_type_intervention_display() if fdr.type_intervention else ""
    if fdr.type_intervention == TypeIntervention.SOUS_TRAITANT and fdr.entreprise_principale_nom:
        intervention += f" de {fdr.entreprise_principale_nom}"

    if fdr.activite_couverte is False:
        activites = (
            "ATTENTION : l'activité suivante ne fait pas partie des activités déclarées au contrat et "
            f"n'est pas garantie en l'état : {fdr.activite_non_couverte_precision or 'non précisée'}."
        )
    else:
        activites = "Les travaux désignés ci-dessus relèvent des activités déclarées au contrat de l'assuré."

    est_definitive = kind == KindAttestation.DEFINITIVE
    numero = (
        attestation.numero
        if attestation and attestation.numero
        else (f"PROJET-{demande.reference}" if not est_definitive else "À ATTRIBUER À LA VALIDATION")
    )
    date_edition = (
        attestation.validated_at.date() if attestation and attestation.validated_at else timezone.now().date()
    )
    debut_contrat, fin_contrat = periode_contrat(date_edition)
    signataire = signataire or (attestation.validated_by if attestation else None)
    signataire_defaut = format_attestation["signataire"]
    siret = fdr.assure_siret or ""

    return {
        "assure_nom": fdr.assure_nom or "",
        "assure_adresse": fdr.assure_adresse or "",
        "assure_cp_ville": " ".join(p for p in (fdr.assure_code_postal, fdr.assure_ville) if p),
        "assure_ville": fdr.assure_ville or "",
        # SIRET présenté par groupes comme sur le modèle (833 207 194 00014)
        "assure_siret": f"{siret[:3]} {siret[3:6]} {siret[6:9]} {siret[9:]}" if len(siret) == 14 else siret,
        "numero_contrat": fdr.numero_contrat or "",
        "reference_client": fdr.reference_client or "",
        "produit": format_attestation["produit"],
        "contrat_periode_debut": format_date(debut_contrat),
        "contrat_periode_fin": format_date(fin_contrat),
        "plafond_cout": format_attestation["plafond_cout_construction"],
        "chantier_nom": fdr.chantier_nom or "",
        "chantier_ville": fdr.chantier_ville or "",
        "type_chantier": nature,
        "usage": usage,
        "date_debut": format_date(fdr.date_debut),
        "date_fin": format_date(fdr.date_fin),
        "cout_total": f"{format_montant(fdr.cout_total)} € HT" if fdr.cout_total is not None else "",
        "montant_prestation": f"{format_montant(fdr.montant_prestation)} € HT"
        if fdr.montant_prestation is not None
        else "",
        "type_intervention": intervention,
        "description_travaux": fdr.description_travaux or "",
        "activites_garanties": activites,
        "intermediaire_nom": distributeur.organisation or distributeur.nom_affichage,
        "intermediaire_adresse": distributeur.adresse,
        "intermediaire_telephone": distributeur.telephone,
        "intermediaire_email": distributeur.email,
        "distributeur_nom": f"{distributeur.nom_affichage}"
        + (f" – {distributeur.organisation}" if distributeur.organisation else ""),
        "numero_attestation": numero,
        "date_courrier": format_date(date_edition),
        "date_edition": format_date_longue(date_edition),
        "lieu_signature": format_attestation["lieu_signature"],
        "signataire_nom": signataire_defaut["nom"],
        "signataire_titre": signataire_defaut["titre"],
        # Compatibilité avec les contenus enregistrés avant le format officiel.
        "signataire": (
            f"{signataire_defaut['nom']} – {signataire_defaut['titre']}"
            if est_definitive
            else "Projet non signé – à valider par le siège"
        ),
        "valide_par": signataire.nom_affichage if est_definitive and signataire else "",
        "est_projet": not est_definitive,
    }


def entete(variables: dict[str, Any]) -> dict[str, Any]:
    """Cadre non modifiable du document (en-tête et pied de la première page, en-tête courant)."""
    format_attestation = settings.METIER["ATTESTATION"]
    return {
        "accroche": format_attestation["accroche"],
        "intermediaire": {
            "nom": variables["intermediaire_nom"],
            "adresse": variables["intermediaire_adresse"],
            "telephone": variables["intermediaire_telephone"],
            "email": variables["intermediaire_email"],
        },
        "produit": variables["produit"],
        "numero_contrat": variables["numero_contrat"],
        "reference_client": variables["reference_client"],
        "destinataire": {
            "nom": variables["assure_nom"],
            "adresse": variables["assure_adresse"],
            "cp_ville": variables["assure_cp_ville"],
        },
        "date_courrier": variables["date_courrier"],
        "mentions_legales": format_attestation["mentions_legales"],
    }


def corps_initial(variables: dict[str, Any]) -> str:
    """Corps HTML par défaut de l'attestation (format officiel AXA), chips remplies."""
    return render_to_string("attestations/corps_gabarit.html", {"v": variables, "fmt": settings.METIER["ATTESTATION"]})


def rafraichir_chips(html: str, variables: dict[str, Any]) -> str:
    """Remplace le texte de chaque chip `<span data-variable>` par la valeur courante de la variable."""
    soupe = BeautifulSoup(html or "", "html.parser")
    for chip in soupe.find_all("span", attrs={"data-variable": True}):
        cle = chip["data-variable"]
        if cle in variables:
            chip.string = str(variables[cle])
    return str(soupe)


def document_complet(demande: Demande, corps_html: str, variables: dict[str, Any]) -> dict[str, Any]:
    """Contexte du gabarit PDF/prévisualisation : cadre AXA (en-tête, pied, en-tête courant) + corps."""
    return {
        "logo": LOGO_AXA_DATA_URI,
        "assureur": settings.METIER["ASSUREUR"],
        "entete": entete(variables),
        "corps": rafraichir_chips(corps_html, variables),
        "v": variables,
        "demande": demande,
        "est_projet": variables.get("est_projet", True),
    }
