# Déploiement Kubernetes (cluster VPS IONOS)

```
deploy/k8s/
├── base/           # Namespace demo-axa, ConfigMap, PostgreSQL, Mailpit, backend, frontend, Traefik + cert-manager, NetworkPolicy
├── overlays/vps/   # images GHCR (tag fixé par make)
└── secret.env.example
```

## Prérequis

* Contexte kubectl `ionos-vps` (Traefik, cert-manager avec `ClusterIssuer letsencrypt-prod`, StorageClass `local-path`).
* Enregistrement DNS `A demo.zaghratmouncef.com → 217.160.188.117`.
* Images publiées sur GHCR par GitHub Actions (`.github/workflows/ci.yml`) à chaque push sur `main` :
  `ghcr.io/mouncef/demo-attestations-backend` et `ghcr.io/mouncef/demo-attestations-frontend`, tags `latest`
  et `sha-<commit>`.
* `deploy/k8s/secret.env` créé à partir de `secret.env.example`.

## Commandes

```bash
make k8s-install                 # namespace, secret de pull GHCR, secrets applicatifs, déploiement
make k8s-deploy TAG=sha-abc1234  # déployer un tag précis (défaut : latest)
make k8s-status                  # pods, volumes, certificat, route
make k8s-logs                    # logs du backend (migrations, seed, requêtes)
make k8s-seed                    # recréer le jeu de démonstration
make k8s-shell                   # shell Django
make k8s-restart                 # redéployer les images `latest` (nouveau build)
make k8s-destroy                 # supprimer le namespace (données comprises)
```

L'application est servie sur https://demo.zaghratmouncef.com ; la boîte mail de test sur
https://demo.zaghratmouncef.com/mailpit (identifiants `MAILPIT_USER` / `MAILPIT_PASSWORD`).
