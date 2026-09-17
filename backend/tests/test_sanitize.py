"""Sanitisation du HTML de l'éditeur riche : liste blanche, filtre CSS, images incorporées, liens https."""

import base64
import io

from PIL import Image

from apps.attestations.services.sanitize import filtrer_style, sanitiser_html, valider_image


def _png(taille=(4, 4)) -> str:
    tampon = io.BytesIO()
    Image.new("RGB", taille, "red").save(tampon, format="PNG")
    return "data:image/png;base64," + base64.b64encode(tampon.getvalue()).decode()


def test_styles_autorises_conserves_et_interdits_retires():
    assert filtrer_style("color: #00008F; font-size: 12pt; text-align: center") == (
        "color: #00008F; font-size: 12pt; text-align: center"
    )
    assert filtrer_style('font-family: "Source Sans 3", Arial') == 'font-family: "Source Sans 3", Arial'
    assert filtrer_style("font-family: Comic Sans MS") is None
    assert filtrer_style("background: url(http://evil/x.png); color: red") == "color: red"
    assert filtrer_style("position: fixed; z-index: 99; width: expression(alert(1))") is None
    assert filtrer_style("font-size: 900pt") is None and filtrer_style("line-height: 9") is None
    assert filtrer_style("margin-left: 20mm; page-break-after: always") == "margin-left: 20mm; page-break-after: always"


def test_html_riche_conserve():
    html = (
        '<p style="text-align: right; margin-left: 10mm"><span style="color: #ff1721; font-size: 14pt">Texte</span>'
        ' <sup>1</sup> <mark style="background-color: #fff06c">important</mark></p>'
        '<table><tbody><tr><td style="background-color: #e2efff">cellule</td></tr></tbody></table>'
        '<div class="saut-page"></div><a href="https://www.axa.fr/">AXA</a>'
    )
    propre = sanitiser_html(html)
    assert 'style="text-align: right; margin-left: 10mm"' in propre
    assert "<sup>1</sup>" in propre and "<mark" in propre and 'class="saut-page"' in propre
    assert 'href="https://www.axa.fr/"' in propre and 'rel="noopener noreferrer"' in propre


def test_liens_et_scripts_rejetes():
    propre = sanitiser_html('<a href="javascript:alert(1)">x</a><a href="http://insecure/">y</a><script>1</script>')
    assert "href" not in propre and "<script" not in propre and "x" in propre


def test_images_incorporees():
    src = _png()
    propre = sanitiser_html(f'<img src="{src}" alt="tampon" width="50%" style="width: 50%">')
    assert src in propre and 'width="50%"' in propre
    assert valider_image("data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=") is None
    assert valider_image("https://exemple/x.png") is None
    assert valider_image("data:image/png;base64,QUJD") is None  # pas une image
    assert "src" not in sanitiser_html('<img src="https://exemple/x.png">')


def test_image_trop_volumineuse_rejetee(monkeypatch):
    monkeypatch.setattr("apps.attestations.services.sanitize.IMAGE_TAILLE_MAX", 10)
    assert valider_image(_png()) is None
