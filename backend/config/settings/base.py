"""
Settings communs à tous les environnements.

Toute valeur sensible ou dépendante de l'environnement est lue dans les variables
d'environnement (fichier `.env` en docker compose).
Les modules `dev.py`, `prod.py` et `test.py` n'ajustent que ce qui diffère.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers de lecture de l'environnement
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env(name: str, default: str | None = None) -> str:
    """Retourne la variable d'environnement `name` ou `default` ; lève une erreur si absente."""
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(f"Variable d'environnement obligatoire manquante : {name}")
    return value


def env_bool(name: str, default: bool = False) -> bool:
    """Interprète une variable d'environnement comme booléen (1/true/yes/on)."""
    return os.environ.get(name, str(int(default))).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    """Lit une variable d'environnement entière."""
    return int(os.environ.get(name, default))


def env_list(name: str, default: str = "") -> list[str]:
    """Lit une liste séparée par des virgules (valeurs vides ignorées)."""
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Sécurité de base
# ---------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Tierces
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    # Métier
    "apps.core",
    "apps.comptes",
    "apps.demandes",
    "apps.pieces",
    "apps.attestations",
    "apps.documents",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Base de données
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "attestations"),
        "USER": env("POSTGRES_USER", "attestations"),
        "PASSWORD": env("POSTGRES_PASSWORD", ""),
        "HOST": env("POSTGRES_HOST", "localhost"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {"connect_timeout": 5},
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "comptes.User"

# Argon2 en premier : recommandation OWASP pour le hachage des mots de passe.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    # Authentification par JWT porté dans l'en-tête Authorization (pas de cookie → pas de CSRF).
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.core.authentication.JWTAuthenticationActive"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.PaginationStandard",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    # Format d'erreur homogène {"code", "detail", ...} – voir apps.core.exceptions.
    "EXCEPTION_HANDLER": "apps.core.exceptions.handler_exceptions",
    # Limitation de débit : protège le login (force brute) et les uploads.
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/hour",
        "anon": "100/hour",
        "login": "10/min",
        "uploads": "60/hour",
        "analyse_ia": "30/hour",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "API – Demandes d'attestation de chantier (AXA)",
    "DESCRIPTION": (
        "API REST de la plateforme interne de gestion des demandes d'attestation de chantier : "
        "saisie du Formulaire de Déclaration du Risque (FDR), pièces justificatives, scoring de "
        "risque, workflow siège, éditeur d'attestation et analyse de cohérence simulée."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "TAGS": [
        {"name": "auth", "description": "Authentification JWT"},
        {"name": "demandes", "description": "Demandes d'attestation et FDR"},
        {"name": "pieces", "description": "Pièces justificatives"},
        {"name": "attestations", "description": "Projets et attestations définitives, analyse IA"},
        {"name": "notifications", "description": "Notifications in-app"},
        {"name": "referentiels", "description": "Valeurs de référence pour le formulaire dynamique"},
    ],
}

# ---------------------------------------------------------------------------
# CORS / CSRF
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ALLOWED_ORIGINS", "http://localhost:8080")
CORS_ALLOW_CREDENTIALS = False
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:8080")

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Fichiers statiques (admin, Swagger) et médias PRIVÉS
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
# Les pièces jointes et PDF sont stockés HORS webroot : aucune route ne sert MEDIA_ROOT.
# Le téléchargement passe exclusivement par des vues authentifiées (contrôle d'accès).
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))
MEDIA_URL = ""  # volontairement vide : pas d'URL publique
FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = env_int("EMAIL_PORT", 1025)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
EMAIL_TIMEOUT = 5
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "attestations-chantier@axa-demo.fr")
FRONTEND_URL = env("FRONTEND_URL", "http://localhost:8080").rstrip("/")

# ---------------------------------------------------------------------------
# Paramètres métier (règles du FDR, pièces, relances, attestations)
# ---------------------------------------------------------------------------
METIER = {
    # Seuil de coût total au-delà duquel le chantier est considéré comme « gros chantier » (strictement supérieur).
    "SEUIL_GROS_CHANTIER": "10000000.00",
    # Relances : délai entre deux relances et délai après envoi avant la première.
    "RELANCE_COOLDOWN_HOURS": env_int("RELANCE_COOLDOWN_HOURS", 24),
    "RELANCE_DELAI_INITIAL_HOURS": env_int("RELANCE_DELAI_INITIAL_HOURS", 0),
    # Bornes de plausibilité des dates du chantier.
    "FDR_DATE_DEBUT_MAX_PAST_DAYS": 365,
    "FDR_DATE_DEBUT_MAX_FUTURE_DAYS": 3 * 365,
    "FDR_DUREE_MAX_DAYS": 10 * 365,
    # Uploads.
    "UPLOAD_MAX_BYTES": env_int("UPLOAD_MAX_BYTES", 10 * 1024 * 1024),
    "UPLOAD_MAX_PIECES_PAR_DEMANDE": 20,
    "UPLOAD_MAX_TOTAL_BYTES_PAR_DEMANDE": 100 * 1024 * 1024,
    "UPLOAD_ALLOW_OFFICE": env_bool("UPLOAD_ALLOW_OFFICE", False),
    # Analyse IA simulée.
    "IA_SIMULATED_DELAY_MS": env_int("IA_SIMULATED_DELAY_MS", 0),
    # Boîte fonctionnelle du siège (si vide : email à chaque utilisateur SIEGE actif).
    "SIEGE_MAILBOX": env("SIEGE_MAILBOX", ""),
    # Identité de l'assureur imprimée sur les attestations.
    "ASSUREUR": {
        "nom": "AXA France IARD",
        "forme": "Société anonyme au capital de 214 799 030 €",
        "rcs": "722 057 460 R.C.S. Nanterre",
        "adresse": "313 Terrasses de l'Arche – 92727 Nanterre Cedex",
        "mention": (
            "Entreprise régie par le Code des assurances – ACPR, 4 place de Budapest, CS 92459, 75436 Paris Cedex 09"
        ),
    },
    # Format officiel d'attestation AXA France (modèle « attestation-assurance-chantier.pdf ») : valeurs par
    # défaut reprises dans le gabarit, rectifiables par le siège dans l'éditeur avant validation.
    "ATTESTATION": {
        "accroche": "réinventons / notre métier",
        "assureur_atteste": "AXA France, dont le siège social est situé Terrasses de l'Arche 92000 Nanterre",
        "produit": "BTPlus Concept",
        "plafond_cout_construction": "2 000 000 €",
        "lieu_signature": "Nanterre",
        "signataire": {"nom": "Mathieu GODART", "titre": "Directeur Général Délégué d'AXA France"},
        "mentions_legales": (
            "AXA France IARD S.A. au capital de 214 799 030 €. 722 057 460 R.C.S. Nanterre. TVA intracommunautaire "
            "n° FR 14 722 057 460 • AXA Assurances IARD Mutuelle. Société d'Assurance Mutuelle à cotisations fixes "
            "contre l'incendie, les accidents et risques divers. Siren 775 699 309. TVA intracommunautaire "
            "n° FR 39 775 699 309. Sièges sociaux : 313, Terrasses de l'Arche – 92727 Nanterre Cedex • Entreprises "
            "régies par le Code des Assurances. Opérations d'assurances exonérées de TVA – art. 261-C CGI – sauf "
            "pour les garanties portées par AXA Assistance France Assurances."
        ),
        # Tableau de garanties du modèle (Garanties / Limite de garantie)
        "franchise": "950 €",
        "plafond_indexation": "15 250 000 euros",
    },
}


# Limite globale de taille des requêtes (multipart) alignée sur la taille max d'une pièce
# avec une marge pour les champs du formulaire.
DATA_UPLOAD_MAX_MEMORY_SIZE = METIER["UPLOAD_MAX_BYTES"] + 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024  # au-delà, Django écrit dans un fichier temporaire

# ---------------------------------------------------------------------------
# Journalisation
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s [%(name)s] %(message)s"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"level": "WARNING"},
        "apps": {"level": "INFO"},
        "securite": {"level": "WARNING"},
        "weasyprint": {"level": "WARNING"},
        "fontTools": {"level": "WARNING"},
    },
}
