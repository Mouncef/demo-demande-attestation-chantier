# Plateforme de gestion des demandes d'attestation de chantier

Application web interne permettant aux distributeurs (agents généraux, courtiers) de déclarer un risque chantier,
de constituer le dossier de pièces justificatives et de l'envoyer au siège pour instruction et émission de
l'attestation.

## Prérequis

Docker Desktop (Windows / macOS) ou Docker Engine avec le plugin compose (Linux).

## Démarrage

```bash
cp .env.example .env   # facultatif : valeurs de développement intégrées
docker compose up --build
```

* Application : http://localhost:8080
* API : http://localhost:8080/api/docs/ (Swagger UI)
* Sonde de santé : http://localhost:8080/health/
* Boîte mail de test (Mailpit) : http://localhost:8025

Le port peut être changé avec `FRONTEND_PORT` dans `.env`.

Au premier démarrage, les migrations sont appliquées et un jeu de démonstration est créé (comptes et demandes à
différents statuts). Désactivable avec `SEED_DEMO_DATA=0`.

### Comptes de démonstration

Mot de passe commun : `Axa-Demo-2026!` (variable `DEMO_PASSWORD`).

| Compte | Rôle |
|---|---|
| `distributeur@axa-demo.fr` | Distributeur (agent général) |
| `distributeur2@axa-demo.fr` | Distributeur (courtier) |
| `siege@axa-demo.fr` | Siège |
| `admin@axa-demo.fr` | Administration Django (`/admin/`) |

## Stack

* Backend : Python 3.13 · Django 5.2 · Django REST Framework · PostgreSQL 16 · authentification JWT
* Frontend : React 19 · TypeScript · Vite · TanStack Query · design system maison (charte AXA)

## Développement

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
```

```bash
cd frontend
npm install
npm run dev        # serveur Vite avec proxy /api vers http://localhost:8000
npm run typecheck && npm run lint && npm test && npm run build
```

## Déploiement Kubernetes

Les images sont construites et publiées sur GHCR par GitHub Actions à chaque push sur `main`
(`ghcr.io/mouncef/demo-attestations-backend`, `ghcr.io/mouncef/demo-attestations-frontend`). Le déploiement sur le
cluster (namespace `demo-axa`, Traefik + cert-manager, PostgreSQL et Mailpit inclus) se fait avec `make` :

```bash
cp deploy/k8s/secret.env.example deploy/k8s/secret.env   # puis renseigner les valeurs
make k8s-install                                         # namespace, secrets, déploiement
make k8s-status
```

* Application : https://demo.zaghratmouncef.com
* Boîte mail de test : https://demo.zaghratmouncef.com/mailpit (authentification basique)

Détails et autres cibles (`k8s-deploy TAG=…`, `k8s-logs`, `k8s-seed`, `k8s-restart`) dans
[deploy/k8s/README.md](deploy/k8s/README.md).
