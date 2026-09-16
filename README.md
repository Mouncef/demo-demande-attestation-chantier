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

* API : http://localhost:8000/api/docs/ (Swagger UI)
* Sonde de santé : http://localhost:8000/health/

## Stack

Python 3.13 · Django 5.2 · Django REST Framework · PostgreSQL 16 · authentification JWT.

## Développement

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check . && ruff format --check .
```
