"""
Commande `regenerer_pdf_fdr` : régénère le PDF de chaque soumission de FDR à partir de son snapshot.

Utile après une évolution du gabarit (charte, logo, mentions). Le contenu métier reste celui figé
à l'envoi : les données proviennent de `SoumissionFDR.fdr_snapshot`, `pieces_snapshot` et
`scoring_snapshot`, jamais du FDR courant.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.core.utils import format_date, format_montant
from apps.demandes.models import FDR, SoumissionFDR
from apps.documents.logo import LOGO_AXA_DATA_URI
from apps.documents.pdf import rendre_pdf

CHAMPS_FDR = {f.name for f in FDR._meta.fields if f.name not in ("demande", "created_at", "updated_at")}
CHAMPS_DATE = {"date_debut", "date_fin"}
CHAMPS_MONTANT = {"cout_total", "montant_prestation"}


def _depuis_snapshot(snapshot: dict) -> FDR:
    """Reconstruit une instance FDR (non persistée) : le snapshot JSON stocke dates et montants en texte."""
    valeurs = {}
    for cle, valeur in snapshot.items():
        if cle not in CHAMPS_FDR:
            continue
        if valeur is not None and cle in CHAMPS_DATE:
            valeur = date.fromisoformat(valeur)
        elif valeur is not None and cle in CHAMPS_MONTANT:
            valeur = Decimal(valeur)
        valeurs[cle] = valeur
    return FDR(**valeurs)


class Command(BaseCommand):
    help = "Régénère les PDF des soumissions de FDR (gabarit à jour, données figées à l'envoi)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--reference", help="Limiter à une demande (ex. DEM-2026-000003)")

    def handle(self, *args, **options) -> None:
        soumissions = SoumissionFDR.objects.select_related("demande__distributeur").order_by("created_at")
        if options["reference"]:
            soumissions = soumissions.filter(demande__reference=options["reference"])

        nb = 0
        for soumission in soumissions:
            snapshot = soumission.fdr_snapshot or {}
            # Instance non persistée : donne accès aux libellés (`get_*_display`) du gabarit.
            fdr = _depuis_snapshot(snapshot)
            demande = soumission.demande
            # Le gabarit lit `demande.nb_soumissions` et le commentaire : on présente ceux de l'envoi concerné.
            demande.nb_soumissions = soumission.numero
            demande.commentaire_distributeur = soumission.commentaire_distributeur
            pieces = soumission.pieces_snapshot or []
            contexte = {
                "logo": LOGO_AXA_DATA_URI,
                "demande": demande,
                "fdr": fdr,
                "distributeur": demande.distributeur,
                "date_edition": format_date(soumission.created_at.date()),
                "date_debut": format_date(fdr.date_debut),
                "date_fin": format_date(fdr.date_fin),
                "cout_total": format_montant(fdr.cout_total),
                "montant_prestation": format_montant(fdr.montant_prestation),
                "scoring": soumission.scoring_snapshot,
                "completude": {
                    "exigences": [p for p in pieces if "niveau" in p],
                    "pieces_hors_exigence": [p for p in pieces if "niveau" not in p],
                },
            }
            pdf = rendre_pdf("pdf/fdr.html", contexte)
            ancien = soumission.pdf.name
            soumission.pdf.save(f"FDR-{demande.reference}-{soumission.numero}.pdf", ContentFile(pdf), save=True)
            if ancien and ancien != soumission.pdf.name:
                soumission.pdf.storage.delete(ancien)
            nb += 1
            self.stdout.write(f"{demande.reference} – envoi n°{soumission.numero} : PDF régénéré")
        self.stdout.write(self.style.SUCCESS(f"{nb} PDF régénéré(s)."))
