"""
Sanitisation du HTML produit par l'éditeur riche.

Liste blanche stricte (nh3 / ammonia) : balises de mise en forme et tableaux uniquement, pas de
liens, d'images ni de scripts. Les « chips » de variables sont des `<span data-variable="…">`.
"""

from __future__ import annotations

import nh3

BALISES = {
    "p",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "h1",
    "h2",
    "h3",
    "h4",
    "ul",
    "ol",
    "li",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "span",
    "div",
    "blockquote",
    "hr",
}
# Les classes portent la mise en page du format officiel (titre centré, sections alignées à droite,
# tableau de garanties, notes, bloc signature) : elles sont conservées sur les blocs concernés.
ATTRIBUTS = {
    "span": {"data-variable", "data-label", "class"},
    "div": {"class"},
    "p": {"class"},
    "h1": {"class"},
    "h2": {"class"},
    "h3": {"class"},
    "table": {"class"},
    "tr": {"class"},
    "ul": {"class"},
    "ol": {"class"},
    "li": {"class"},
    "td": {"colspan", "rowspan", "class"},
    "th": {"colspan", "rowspan", "class"},
}


def sanitiser_html(html: str) -> str:
    """Nettoie le HTML : supprime tout ce qui n'est pas explicitement autorisé."""
    return nh3.clean(html or "", tags=BALISES, attributes=ATTRIBUTS, strip_comments=True, link_rel=None)
