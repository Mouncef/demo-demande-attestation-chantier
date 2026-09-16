#!/usr/bin/env bash
# =============================================================================
# Point d'entrée du conteneur backend :
#   1. attend que PostgreSQL accepte les connexions ;
#   2. applique les migrations ;
#   3. collecte les fichiers statiques (admin, Swagger) ;
#   4. crée les données de démonstration si SEED_DEMO_DATA=1 (idempotent) ;
#   5. lance la commande passée en argument (gunicorn par défaut).
# =============================================================================
set -euo pipefail

echo "[entrypoint] Attente de PostgreSQL sur ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}…"
until pg_isready -h "${POSTGRES_HOST:-db}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-postgres}" -q; do
  sleep 1
done
echo "[entrypoint] PostgreSQL prêt."

python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear >/dev/null

if [ "${SEED_DEMO_DATA:-0}" = "1" ]; then
  echo "[entrypoint] Création des données de démonstration (idempotent)…"
  python manage.py seed_demo
fi

echo "[entrypoint] Démarrage : $*"
exec "$@"
