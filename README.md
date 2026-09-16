# Plateforme de gestion des demandes d'attestation de chantier

Application web interne permettant à un **distributeur** (agent général, courtier) de déclarer un risque chantier
via un Formulaire de Déclaration du Risque (FDR), de joindre les pièces justificatives exigées par les règles
métier et d'envoyer la demande au **siège**, puis au siège de l'instruire (accepter, refuser, demander des
compléments) et d'établir l'**attestation de chantier** au format officiel AXA dans un éditeur riche, avec une
analyse de cohérence entre le FDR et l'attestation.

Ce document décrit l'installation et l'utilisation. Les choix techniques sont détaillés dans
[docs/CHOIX_TECHNIQUES.md](docs/CHOIX_TECHNIQUES.md).

Démo en ligne : https://demo.zaghratmouncef.com

---

## 1. Prérequis

| Usage | Outils |
|---|---|
| Lancer la plateforme | Docker Desktop (Windows, macOS) ou Docker Engine 24+ avec le plugin compose (Linux) |
| Développer | Python 3.13, Node.js 22, PostgreSQL 16 (ou le conteneur `db` du compose) |
| Déployer sur Kubernetes | `kubectl`, `make`, `htpasswd` (paquet `apache2-utils`), accès au cluster |

Aucune autre dépendance n'est nécessaire pour la première option : les images embarquent tout (WeasyPrint,
libmagic, polices, gunicorn, nginx).

## 2. Démarrage en une commande

```bash
git clone https://github.com/Mouncef/demo-demande-attestation-chantier.git
cd demo-demande-attestation-chantier
cp .env.example .env        # facultatif : des valeurs de développement sont intégrées
docker compose up --build
```

Au premier démarrage (3 à 5 minutes de construction), la plateforme :

1. démarre PostgreSQL et Mailpit (serveur SMTP de test) ;
2. applique les migrations et crée le **jeu de démonstration** (comptes et demandes à différents statuts) ;
3. sert l'application sur http://localhost:8080.

| Service | URL |
|---|---|
| Application | http://localhost:8080 |
| Documentation de l'API (Swagger UI) | http://localhost:8080/api/docs/ |
| Schéma OpenAPI | http://localhost:8080/api/schema/ |
| Boîte mail de test (Mailpit) | http://localhost:8025 |
| Administration Django | http://localhost:8080/admin/ |
| Sonde de santé | http://localhost:8080/health/ |

Le port public se change avec `FRONTEND_PORT` dans `.env`. Sous Windows, le fichier `.gitattributes` force les
fins de ligne LF sur les scripts : aucun réglage n'est nécessaire.

Commandes utiles (`make help` pour la liste complète) :

```bash
make up        # démarre en arrière-plan (build inclus)
make logs      # suit les logs
make down      # arrête (les volumes sont conservés)
make seed      # recrée le jeu de démonstration
make test      # tests backend et frontend
```

## 3. Comptes de démonstration

Mot de passe commun : `Axa-Demo-2026!` (variable `DEMO_PASSWORD`).

| Compte | Rôle | Usage |
|---|---|---|
| `distributeur@axa-demo.fr` | Distributeur (agent général) | Saisie du FDR, pièces, envoi, projet d'attestation |
| `distributeur2@axa-demo.fr` | Distributeur (courtier) | Vérifier l'isolation des données entre distributeurs |
| `siege@axa-demo.fr` | Siège | Instruction, décision, attestation définitive, reporting global |
| `admin@axa-demo.fr` | Superutilisateur | Administration Django |

## 4. Parcours de démonstration

1. **Distributeur** : ouvrir un brouillon, compléter le FDR (le bandeau « Pièces qui seront requises » se met à
   jour en direct), passer à l'étape *Risque & pièces* (score de risque, dépôt des pièces par glisser-déposer),
   puis *Validation & envoi*. L'envoi est bloqué tant que le FDR est invalide ou le dossier incomplet.
2. **Siège** : la demande apparaît avec son score figé ; demander des compléments (la main revient au
   distributeur), accepter ou refuser avec motif. Chaque action notifie l'autre partie (cloche et email visible
   dans Mailpit).
3. **Attestation** : après acceptation, le distributeur prépare un projet d'attestation (gabarit officiel AXA
   pré-rempli, zones dynamiques issues du FDR) et le soumet au siège. Le siège reprend le projet, le rectifie,
   lance l'analyse de cohérence (incohérences surlignées dans le texte) et valide l'attestation définitive :
   numéro, PDF et notification au distributeur.
4. **Reporting** : indicateurs et graphiques par période, globaux pour le siège, restreints à ses demandes pour
   un distributeur.

## 5. Configuration

Toutes les valeurs sont lues dans les variables d'environnement (fichier `.env`, voir `.env.example`) :

| Variable | Rôle | Défaut |
|---|---|---|
| `DJANGO_SECRET_KEY` | clé secrète Django (obligatoire, unique par environnement) | valeur de développement |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CORS_ALLOWED_ORIGINS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | hôtes et origines autorisés | `localhost` |
| `FRONTEND_URL` | URL publique utilisée dans les emails | `http://localhost:8080` |
| `POSTGRES_*` | connexion PostgreSQL | conteneur `db` |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL`, `SIEGE_MAILBOX` | SMTP et boîte fonctionnelle du siège | Mailpit |
| `RELANCE_COOLDOWN_HOURS`, `RELANCE_DELAI_INITIAL_HOURS` | délais de relance | 24 h, 0 |
| `UPLOAD_MAX_BYTES`, `UPLOAD_ALLOW_OFFICE` | pièces jointes | 10 Mo, PDF et images seulement |
| `IA_SIMULATED_DELAY_MS` | latence simulée de l'analyse de cohérence | 800 ms |
| `SEED_DEMO_DATA`, `DEMO_PASSWORD` | jeu de démonstration | activé |

## 6. Développement

### Backend

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
export DJANGO_SECRET_KEY=dev POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5432 POSTGRES_PASSWORD=attestations-dev-password
python manage.py migrate && python manage.py seed_demo
python manage.py runserver          # http://localhost:8000
pytest                              # tests (base de test créée automatiquement)
ruff check . && ruff format --check .
```

Une base PostgreSQL locale est nécessaire, par exemple `docker compose up -d db`.

### Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173, proxy /api vers http://localhost:8000
npm run typecheck && npm run lint && npm test && npm run build
```

### Qualité

* Backend : 80 tests pytest (validation du FDR, exigences, scoring, workflow et droits, relance, pièces,
  attestations, analyse de cohérence, authentification), ruff (lint et format).
* Frontend : vitest (schéma zod, règles de pièces, composants, formatage), eslint, prettier, tsc.
* Intégration continue : `.github/workflows/ci.yml` exécute ces contrôles, valide les manifestes Kubernetes et
  publie les images sur GHCR à chaque push sur `main`.

## 7. Déploiement Kubernetes

Les images `ghcr.io/mouncef/demo-attestations-backend` et `ghcr.io/mouncef/demo-attestations-frontend` sont
construites par GitHub Actions (tags `latest`, `sha-<commit>`, version sur tag `v*`). Le déploiement sur le
cluster (namespace `demo-axa`, Traefik et cert-manager, PostgreSQL et Mailpit inclus) se fait avec `make` :

```bash
cp deploy/k8s/secret.env.example deploy/k8s/secret.env   # renseigner les valeurs
make k8s-install                                         # namespace, secret de pull, secrets, déploiement
make k8s-status                                          # pods, volumes, certificat, route
make k8s-deploy TAG=sha-abc1234                          # déployer un tag précis
make k8s-restart                                         # reprendre les images latest après un build
make k8s-logs | k8s-seed | k8s-shell | k8s-mailpit | k8s-destroy
```

* Application : https://demo.zaghratmouncef.com
* Boîte mail de test : https://demo.zaghratmouncef.com/mailpit (authentification basique, identifiants dans
  `secret.env`)

Détails dans [deploy/k8s/README.md](deploy/k8s/README.md).

## 8. Structure du dépôt

```
├── backend/                 # API Django : apps core, comptes, demandes, pieces, attestations, documents, notifications
│   ├── config/settings/     # base / dev / prod / test
│   ├── templates/pdf/       # gabarits WeasyPrint (FDR, attestation)
│   └── tests/               # pytest
├── frontend/                # React + TypeScript (Vite) : api/, design-system/, features/, lib/
├── deploy/k8s/              # Kustomize (base + overlay VPS)
├── docs/CHOIX_TECHNIQUES.md # architecture, règles métier, sécurité, justification des choix
├── docker-compose.yml       # db, mailpit, backend, frontend
├── Makefile                 # raccourcis compose et déploiement Kubernetes
└── .github/workflows/ci.yml # tests, validation K8s, images GHCR
```
