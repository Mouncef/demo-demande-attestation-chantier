"""Logo AXA officiel (PNG) encodé en data URI pour les PDF – aucune ressource réseau au rendu."""

import base64
from pathlib import Path

_CHEMIN = Path(__file__).resolve().parent / "assets" / "logo-axa.png"

LOGO_AXA_PNG: bytes = _CHEMIN.read_bytes()
LOGO_AXA_DATA_URI = "data:image/png;base64," + base64.b64encode(LOGO_AXA_PNG).decode()
