# =============================================================================
# Image backend – build multi-étapes, exécution en utilisateur non-root.
#   * étape « builder » : installe les dépendances Python dans un venv
#   * étape « runtime » : image slim + bibliothèques natives de WeasyPrint/libmagic
# =============================================================================
FROM python:3.13-slim AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build

# Outils de compilation nécessaires à certaines roues (argon2, psycopg…)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
# Installation dans un venv isolé que l'on copiera dans l'image finale.
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install ".[dev]"

# -----------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod

# Bibliothèques natives : WeasyPrint (pango/cairo/harfbuzz), libmagic (détection MIME),
# polices (rendu PDF), client PostgreSQL (attente de la base dans l'entrypoint).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 libcairo2 libgdk-pixbuf-2.0-0 \
        libffi8 shared-mime-info fonts-liberation fonts-dejavu-core \
        libmagic1 postgresql-client curl \
    && rm -rf /var/lib/apt/lists/*

# Utilisateur applicatif sans privilèges.
RUN groupadd --system app && useradd --system --gid app --home /app --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app . .

# Répertoires de données (média privé) et de fichiers statiques.
RUN mkdir -p /data/media /app/staticfiles && chown -R app:app /data /app \
    && chmod +x /app/entrypoint.sh

USER app
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8000/health/ || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--access-logfile", "-"]
