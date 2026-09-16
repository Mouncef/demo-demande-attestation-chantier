"""Settings des tests automatisés : rapides et déterministes."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "cle-de-test-non-secrete-0123456789abcdef0123456789")

from .base import *  # noqa: E402,F401,F403
from .base import BASE_DIR, METIER, REST_FRAMEWORK  # noqa: E402

DEBUG = False

# Hachage rapide : les tests créent beaucoup d'utilisateurs.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Emails capturés en mémoire (django.core.mail.outbox).
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Médias dans un répertoire temporaire isolé.
MEDIA_ROOT = BASE_DIR / ".test-media"

# Pas de latence artificielle ni de throttling pendant les tests.
METIER["IA_SIMULATED_DELAY_MS"] = 0
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []

# Journalisation réduite au strict nécessaire pendant les tests.
LOGGING["root"]["level"] = "ERROR"  # noqa: F405
