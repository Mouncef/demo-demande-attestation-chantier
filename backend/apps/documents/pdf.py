"""
Rendu PDF à partir de gabarits HTML Django.

WeasyPrint est configuré sans accès réseau ni système de fichiers : seules les ressources
`data:` (logo incorporé) sont autorisées. Les polices sont celles installées dans l'image
(Liberation / DejaVu) avec repli générique.
"""

from __future__ import annotations

from typing import Any

from django.template.loader import render_to_string
from weasyprint import HTML
from weasyprint.urls import URLFetcher

# Défense contre l'exfiltration / SSRF via du HTML injecté : uniquement les URI `data:`.
FETCHER_SANS_RESEAU = URLFetcher(allowed_protocols={"data"}, fail_on_errors=False)


def rendre_pdf(template: str, contexte: dict[str, Any]) -> bytes:
    """Rend le gabarit `template` avec `contexte` et renvoie les octets du PDF."""
    html = render_to_string(template, contexte)
    return HTML(string=html, base_url=None, url_fetcher=FETCHER_SANS_RESEAU).write_pdf()
