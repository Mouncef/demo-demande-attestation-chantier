"""Settings de développement (docker compose local)."""

from .base import *  # noqa: F401,F403
from .base import env_bool

DEBUG = env_bool("DJANGO_DEBUG", True)

# En dev, le schéma OpenAPI et l'admin sont servis par Django directement.
INTERNAL_IPS = ["127.0.0.1"]
