"""
Sanitisation du HTML produit par l'éditeur riche.

Liste blanche stricte (nh3 / ammonia) : balises de mise en forme, tableaux, images incorporées et liens https
uniquement ; pas de script ni de contenu externe. Les « chips » de variables sont des `<span data-variable="…">`.

L'éditeur WYSIWYG produit des styles en ligne (police, taille, couleurs, alignement, retraits, interligne,
fond de cellule, largeur d'image) : l'attribut `style` est accepté mais **filtré propriété par propriété**
(liste blanche, valeurs contrôlées par expressions régulières, aucune URL ni expression). Les images sont
limitées au PNG / JPEG incorporé en base64 (1 Mo décodé) et vérifiées avec Pillow ; les liens au schéma https.
"""

from __future__ import annotations

import base64
import binascii
import io
import re

import nh3
from PIL import Image, UnidentifiedImageError

BALISES = {
    "p",
    "br",
    "strong",
    "b",
    "em",
    "i",
    "u",
    "s",
    "sub",
    "sup",
    "mark",
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
    "img",
    "a",
}
# Les classes portent la mise en page du format officiel (titre centré, sections alignées à droite,
# tableau de garanties, notes, bloc signature, saut de page) : elles sont conservées sur les blocs concernés.
ATTRIBUTS = {
    "span": {"data-variable", "data-label", "class", "style"},
    "mark": {"style"},
    "div": {"class", "style"},
    "p": {"class", "style"},
    "h1": {"class", "style"},
    "h2": {"class", "style"},
    "h3": {"class", "style"},
    "table": {"class", "style"},
    "tr": {"class"},
    "ul": {"class"},
    "ol": {"class", "start"},
    "li": {"class", "style"},
    "td": {"colspan", "rowspan", "class", "style"},
    "th": {"colspan", "rowspan", "class", "style"},
    "img": {"src", "alt", "width", "style"},
    "a": {"href"},
}

# Familles de polices proposées par l'éditeur ; toutes sont installées dans l'image (rendu PDF) et déclarées
# avec leurs replis métriquement compatibles (Liberation ↔ Arial / Times New Roman / Courier New).
POLICES_AUTORISEES = (
    "Source Sans 3",
    "Source Serif 4",
    "Liberation Sans",
    "Liberation Serif",
    "Liberation Mono",
    "DejaVu Sans",
    "Arial",
    "Helvetica",
    "Times New Roman",
    "Courier New",
    "Georgia",
    "sans-serif",
    "serif",
    "monospace",
)
IMAGE_TAILLE_MAX = 1024 * 1024  # 1 Mo décodé
IMAGE_FORMATS = {"PNG", "JPEG"}

_COULEUR = (
    r"(#[0-9a-fA-F]{3,8}|rgba?\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*(,\s*(0|1|0?\.\d+)\s*)?\)|[a-zA-Z]{3,20})"
)
_LONGUEUR = r"(0|-?\d{1,3}(\.\d{1,2})?(px|pt|mm|em|rem|%))"
# Propriété CSS autorisée → expression régulière que sa valeur entière doit respecter.
PROPRIETES_CSS: dict[str, re.Pattern[str]] = {
    "color": re.compile(rf"^{_COULEUR}$"),
    "background-color": re.compile(rf"^{_COULEUR}$"),
    "background": re.compile(rf"^{_COULEUR}$"),
    "font-family": re.compile(r"^[\w\s,'\"-]{1,120}$"),
    "font-size": re.compile(r"^([6-9]|[1-6]\d|7[0-2])(\.\d)?(pt|px)$"),
    "font-weight": re.compile(r"^(normal|bold|[1-9]00)$"),
    "font-style": re.compile(r"^(normal|italic)$"),
    "line-height": re.compile(r"^([1-3](\.\d{1,2})?|normal)$"),
    "text-align": re.compile(r"^(left|center|right|justify)$"),
    "text-decoration": re.compile(r"^(none|underline|line-through)( (underline|line-through))?$"),
    "vertical-align": re.compile(r"^(top|middle|bottom|baseline|sub|super)$"),
    "margin-left": re.compile(rf"^{_LONGUEUR}$"),
    "padding-left": re.compile(rf"^{_LONGUEUR}$"),
    "text-indent": re.compile(rf"^{_LONGUEUR}$"),
    "width": re.compile(r"^(\d{1,3}(\.\d)?%|\d{1,4}px|auto)$"),
    "height": re.compile(r"^(\d{1,4}px|auto)$"),
    "page-break-after": re.compile(r"^(always|avoid|auto)$"),
    "page-break-before": re.compile(r"^(always|avoid|auto)$"),
    "break-after": re.compile(r"^(page|avoid|auto)$"),
}
_INTERDIT = re.compile(r"(url\s*\(|expression|@|\\|javascript|<|>)", re.IGNORECASE)


def filtrer_style(style: str) -> str | None:
    """Ne conserve que les déclarations CSS autorisées ; renvoie None si rien ne subsiste."""
    conservees: list[str] = []
    for declaration in style.split(";"):
        if ":" not in declaration:
            continue
        propriete, valeur = (part.strip() for part in declaration.split(":", 1))
        propriete = propriete.lower()
        valeur = re.sub(r"\s*!important$", "", valeur)
        motif = PROPRIETES_CSS.get(propriete)
        if not motif or _INTERDIT.search(valeur) or not motif.match(valeur):
            continue
        if propriete == "font-family":
            familles = [f.strip().strip("'\"") for f in valeur.split(",")]
            if not familles or any(f not in POLICES_AUTORISEES for f in familles):
                continue
            valeur = ", ".join(f'"{f}"' if " " in f else f for f in familles)
        conservees.append(f"{propriete}: {valeur}")
    return "; ".join(conservees) if conservees else None


def valider_image(src: str) -> str | None:
    """Accepte uniquement une image PNG / JPEG incorporée (`data:`), de taille bornée et décodable."""
    m = re.match(r"^data:image/(png|jpeg|jpg);base64,([A-Za-z0-9+/=\s]+)$", src)
    if not m:
        return None
    try:
        octets = base64.b64decode(re.sub(r"\s", "", m.group(2)), validate=True)
    except (binascii.Error, ValueError):
        return None
    if not octets or len(octets) > IMAGE_TAILLE_MAX:
        return None
    try:
        with Image.open(io.BytesIO(octets)) as image:
            if image.format not in IMAGE_FORMATS:
                return None
            image.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        return None
    return src


def _filtrer_attribut(balise: str, attribut: str, valeur: str) -> str | None:
    if attribut == "style":
        return filtrer_style(valeur)
    if balise == "img" and attribut == "src":
        return valider_image(valeur)
    if balise == "img" and attribut == "width":
        return valeur if re.match(r"^\d{1,4}(%|px)?$", valeur) else None
    if balise == "a" and attribut == "href":
        return valeur if re.match(r"^https://[^\s<>\"']{1,2000}$", valeur, re.IGNORECASE) else None
    if attribut == "class":
        return valeur if re.match(r"^[\w -]{1,80}$", valeur) else None
    return valeur


def sanitiser_html(html: str) -> str:
    """Nettoie le HTML : supprime tout ce qui n'est pas explicitement autorisé."""
    return nh3.clean(
        html or "",
        tags=BALISES,
        attributes=ATTRIBUTS,
        attribute_filter=_filtrer_attribut,
        url_schemes={"https", "data"},
        link_rel="noopener noreferrer",
        strip_comments=True,
    )
