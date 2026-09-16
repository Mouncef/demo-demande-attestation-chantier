"""
Commande `seed_demo` : crée les comptes et demandes de démonstration (idempotente).

Comptes (mot de passe : variable DEMO_PASSWORD, voir README) :
  * distributeur@axa-demo.fr   – agent général (DISTRIBUTEUR)
  * distributeur2@axa-demo.fr  – courtier (DISTRIBUTEUR), pour vérifier l'isolation des données
  * siege@axa-demo.fr          – souscripteur siège (SIEGE)
  * admin@axa-demo.fr          – superuser (accès /admin)
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.attestations.services import cycle
from apps.comptes.models import Role, User
from apps.demandes.models import Demande
from apps.demandes.services import workflow
from apps.pieces.models import PieceJointe, TypePiece

# PDF minimal valide (une page blanche) utilisé comme pièce de démonstration.
PDF_MINIMAL = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000101 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n160\n%%EOF\n"
)


class Command(BaseCommand):
    help = "Crée les comptes et demandes de démonstration (idempotent)."

    def handle(self, *args, **options) -> None:
        mot_de_passe = os.environ.get("DEMO_PASSWORD", "Axa-Demo-2026!")
        utilisateurs = self._comptes(mot_de_passe)
        if Demande.objects.exists():
            self.stdout.write("Demandes déjà présentes : seed des demandes ignoré.")
            return
        self._demandes(utilisateurs)
        self.stdout.write(self.style.SUCCESS("Données de démonstration créées."))

    # ------------------------------------------------------------------ comptes
    def _comptes(self, mot_de_passe: str) -> dict[str, User]:
        definitions = [
            (
                "distributeur@axa-demo.fr",
                Role.DISTRIBUTEUR,
                "Claire",
                "Martin",
                "Agence AXA Martin – Lyon",
                "AG-69001",
                False,
            ),
            (
                "distributeur2@axa-demo.fr",
                Role.DISTRIBUTEUR,
                "Karim",
                "Benali",
                "Cabinet Benali Courtage – Marseille",
                "CO-13002",
                False,
            ),
            ("siege@axa-demo.fr", Role.SIEGE, "Sophie", "Durand", "AXA France – Souscription Construction", "", False),
            ("admin@axa-demo.fr", Role.SIEGE, "Admin", "Plateforme", "AXA France – DSI", "", True),
        ]
        resultat: dict[str, User] = {}
        for email, role, prenom, nom, organisation, code, admin in definitions:
            user, cree = User.objects.get_or_create(
                email=email,
                defaults={
                    "role": role,
                    "first_name": prenom,
                    "last_name": nom,
                    "organisation": organisation,
                    "code_distributeur": code,
                    "is_staff": admin,
                    "is_superuser": admin,
                },
            )
            if cree:
                user.set_password(mot_de_passe)
                user.save()
                self.stdout.write(f"Compte créé : {email} ({role})")
            resultat[email] = user
        return resultat

    # ------------------------------------------------------------------ demandes
    def _fdr(self, demande: Demande, **valeurs) -> None:
        for champ, valeur in valeurs.items():
            setattr(demande.fdr, champ, valeur)
        demande.fdr.save()

    def _piece(self, demande: Demande, code: str, user: User, nom: str) -> None:
        type_piece = TypePiece.objects.get(code=code)
        piece = PieceJointe(
            demande=demande,
            type_piece=type_piece,
            nom_fichier=f"{type_piece.libelle}.pdf",
            nom_original=nom,
            mime="application/pdf",
            taille=len(PDF_MINIMAL),
            deposee_par=user,
            sha256=__import__("hashlib").sha256(PDF_MINIMAL + nom.encode()).hexdigest(),
        )
        piece.fichier.save("piece.pdf", ContentFile(PDF_MINIMAL), save=True)

    @transaction.atomic
    def _demandes(self, u: dict[str, User]) -> None:
        d1, d2, siege = u["distributeur@axa-demo.fr"], u["distributeur2@axa-demo.fr"], u["siege@axa-demo.fr"]
        aujourdhui = date.today()

        # 1. Brouillon simple (construction neuve, aucun déclencheur de pièce)
        brouillon = workflow.creer_demande(d1)
        self._fdr(
            brouillon,
            assure_nom="SAS BÂTI-RHÔNE",
            assure_adresse="14 quai Perrache",
            assure_code_postal="69002",
            assure_siret="83320719400014",
            assure_ville="Lyon",
            numero_contrat="RCD2026LY0142",
            chantier_nom="Résidence Les Terrasses",
            chantier_ville="Villeurbanne",
            type_chantier="CONSTRUCTION_NEUVE",
            usage="HABITATION",
            chantier_atypique=False,
            date_debut=aujourdhui + timedelta(days=30),
            date_fin=aujourdhui + timedelta(days=400),
            cout_total=Decimal("1850000.00"),
            montant_prestation=Decimal("420000.00"),
            type_intervention="ENTREPRISE_PRINCIPALE",
            activite_couverte=True,
            travaux_standards=True,
            description_travaux="Gros œuvre et maçonnerie d'un immeuble de 24 logements en R+4.",
        )

        # 2. Brouillon complexe : rénovation + structure + > 10 M€ + sous-traitant → pièces requises manquantes
        complexe = workflow.creer_demande(d1)
        self._fdr(
            complexe,
            assure_nom="SARL CHARPENTES DUPONT",
            assure_adresse="3 rue des Charpentiers",
            assure_code_postal="38000",
            assure_siret="44306184100047",
            assure_ville="Grenoble",
            numero_contrat="RCD2025GR7781",
            chantier_nom="Réhabilitation Halle Bouchayer",
            chantier_ville="Grenoble",
            type_chantier="RENOVATION",
            modification_structure=True,
            usage="AUTRE",
            usage_autre_precision="Halle industrielle reconvertie en tiers-lieu",
            chantier_atypique=True,
            date_debut=aujourdhui + timedelta(days=15),
            date_fin=aujourdhui + timedelta(days=900),
            cout_total=Decimal("12500000.00"),
            montant_prestation=Decimal("2300000.00"),
            type_intervention="SOUS_TRAITANT",
            entreprise_principale_nom="EIFFAGE CONSTRUCTION",
            activite_couverte=True,
            travaux_standards=False,
            description_travaux=(
                "Reprise de la charpente métallique, renforcement des poteaux et création d'une mezzanine."
            ),
        )

        # 3. Demande envoyée au siège (EN_COURS), dossier complet
        en_cours = workflow.creer_demande(d1)
        self._fdr(
            en_cours,
            assure_nom="EURL PLOMBERIE MOREL",
            assure_adresse="22 avenue de la Libération",
            assure_code_postal="42000",
            assure_siret="55210055400013",
            assure_ville="Saint-Étienne",
            numero_contrat="RCP2024SE3310",
            chantier_nom="Rénovation Clinique du Parc",
            chantier_ville="Saint-Étienne",
            type_chantier="RENOVATION",
            modification_structure=False,
            usage="AUTRE",
            usage_autre_precision="Établissement de santé",
            chantier_atypique=False,
            date_debut=aujourdhui - timedelta(days=10),
            date_fin=aujourdhui + timedelta(days=200),
            cout_total=Decimal("3200000.00"),
            montant_prestation=Decimal("310000.00"),
            type_intervention="SOUS_TRAITANT",
            entreprise_principale_nom="GCC BÂTIMENT",
            activite_couverte=False,
            activite_non_couverte_precision="Réseaux de fluides médicaux (oxygène, vide)",
            travaux_standards=True,
            description_travaux="Plomberie sanitaire et réseaux de fluides médicaux des blocs opératoires.",
        )
        self._piece(en_cours, "DESCRIPTIF_ACTIVITE", d1, "descriptif-fluides-medicaux.pdf")
        self._piece(en_cours, "JUSTIFICATIF_QUALIFICATION", d1, "qualification-qualifelec.pdf")
        self._piece(en_cours, "CONTRAT_SOUS_TRAITANCE", d1, "contrat-sous-traitance-gcc.pdf")
        workflow.envoyer(en_cours.pk, d1, "Dossier complet, merci de votre retour rapide : démarrage imminent.")

        # 4. Demande traitée et acceptée, avec projet d'attestation
        acceptee = workflow.creer_demande(d1)
        self._fdr(
            acceptee,
            assure_nom="SAS ÉLEC-ALPES",
            assure_adresse="8 chemin des Glaisins",
            assure_code_postal="74000",
            assure_siret="73282932000074",
            assure_ville="Annecy",
            numero_contrat="RCD2023AN0099",
            chantier_nom="Groupe scolaire Jean-Moulin",
            chantier_ville="Annecy",
            type_chantier="CONSTRUCTION_NEUVE",
            usage="BUREAU",
            chantier_atypique=False,
            date_debut=aujourdhui - timedelta(days=60),
            date_fin=aujourdhui + timedelta(days=300),
            cout_total=Decimal("4800000.00"),
            montant_prestation=Decimal("650000.00"),
            type_intervention="ENTREPRISE_PRINCIPALE",
            activite_couverte=True,
            travaux_standards=True,
            description_travaux="Installation électrique courants forts et faibles du groupe scolaire.",
        )
        workflow.envoyer(acceptee.pk, d1)
        # Les transitions rechargent la demande : on repart de l'instance renvoyée (statut à jour).
        acceptee = workflow.accepter(acceptee.pk, siege, "Dossier conforme, contrat à jour.")
        gab = cycle.gabarit(acceptee, "PROJET", d1)
        projet = cycle.enregistrer(acceptee, "PROJET", d1, gab["contenu_html"], None)
        cycle.soumettre(acceptee, projet, d1)  # projet soumis : le siège doit établir la définitive

        # 5. Demande refusée
        refusee = workflow.creer_demande(d2)
        self._fdr(
            refusee,
            assure_nom="SARL TOITURES DU SUD",
            assure_adresse="120 avenue du Prado",
            assure_code_postal="13008",
            assure_siret="57200256100015",
            assure_ville="Marseille",
            numero_contrat="RCD2022MA4520",
            chantier_nom="Piscine municipale Luminy",
            chantier_ville="Marseille",
            type_chantier="RENOVATION",
            modification_structure=False,
            usage="COMMERCE",
            chantier_atypique=True,
            date_debut=aujourdhui + timedelta(days=5),
            date_fin=aujourdhui + timedelta(days=120),
            cout_total=Decimal("900000.00"),
            montant_prestation=Decimal("900000.00"),
            type_intervention="ENTREPRISE_PRINCIPALE",
            activite_couverte=False,
            activite_non_couverte_precision="Étanchéité de bassins (activité non souscrite)",
            travaux_standards=False,
            description_travaux="Étanchéité et carrelage des bassins de la piscine municipale.",
        )
        for code, nom in [
            ("DESCRIPTIF_TECHNIQUE", "descriptif-etancheite.pdf"),
            ("PHOTOS_PLANS", "plans-bassins.pdf"),
            ("DESCRIPTIF_ACTIVITE", "activite-etancheite.pdf"),
            ("JUSTIFICATIF_QUALIFICATION", "qualibat.pdf"),
            ("AVIS_TECHNIQUE", "avis-technique-resine.pdf"),
        ]:
            self._piece(refusee, code, d2, nom)
        workflow.envoyer(refusee.pk, d2)
        workflow.refuser(
            refusee.pk,
            siege,
            "Activité d'étanchéité de bassins non souscrite au contrat ; "
            "une extension de garantie doit être étudiée avant toute attestation.",
        )

        # 6. Demande du second distributeur en cours (isolation des données)
        autre = workflow.creer_demande(d2)
        self._fdr(
            autre,
            assure_nom="SAS MENUISERIES PROVENCE",
            assure_adresse="5 cours Mirabeau",
            assure_code_postal="13100",
            assure_siret="32893002700011",
            assure_ville="Aix-en-Provence",
            numero_contrat="RCD2026AX1001",
            chantier_nom="Villa Les Oliviers",
            chantier_ville="Aix-en-Provence",
            type_chantier="CONSTRUCTION_NEUVE",
            usage="HABITATION",
            chantier_atypique=False,
            date_debut=aujourdhui + timedelta(days=20),
            date_fin=aujourdhui + timedelta(days=150),
            cout_total=Decimal("650000.00"),
            montant_prestation=Decimal("85000.00"),
            type_intervention="ENTREPRISE_PRINCIPALE",
            activite_couverte=True,
            travaux_standards=True,
            description_travaux="Fourniture et pose des menuiseries extérieures aluminium et bois.",
        )
        workflow.envoyer(autre.pk, d2)
