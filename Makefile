# Raccourcis de développement (docker compose) et de déploiement Kubernetes (cluster VPS IONOS).
# Sous Windows : utiliser Git Bash ou WSL, ou lancer les commandes docker compose / kubectl directement.
.PHONY: help up down logs build test test-backend test-frontend lint check seed shell \
        k8s-install k8s-namespace k8s-pull-secret k8s-secrets k8s-deploy k8s-restart k8s-status k8s-logs \
        k8s-shell k8s-seed k8s-certificate k8s-mailpit k8s-destroy

# --- Cluster --------------------------------------------------------------------------------
KUBE_CONTEXT ?= ionos-vps
NAMESPACE    ?= demo-axa
REGISTRY     ?= ghcr.io/mouncef
TAG          ?= latest
PULL_SECRET_SOURCE_NS ?= zaghratmouncef
SECRET_ENV   ?= deploy/k8s/secret.env
KUBECTL      := kubectl --context $(KUBE_CONTEXT)
KN           := $(KUBECTL) -n $(NAMESPACE)

help:          ## Liste des cibles
	@grep -E '^[a-zA-Z0-9_-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

# --- Développement local (docker compose) ---------------------------------------------------
up:            ## Démarre toute la plateforme (build inclus)
	docker compose up --build -d
down:          ## Arrête et supprime les conteneurs (volumes conservés)
	docker compose down
logs:          ## Suit les logs
	docker compose logs -f --tail=100
build:         ## Reconstruit les images
	docker compose build
test: test-backend test-frontend
test-backend:  ## Tests backend (pytest) dans le conteneur
	docker compose run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test backend python -m pytest -q
test-frontend: ## Tests frontend (vitest)
	cd frontend && npm test
lint:          ## Lint backend + frontend
	docker compose run --rm --entrypoint sh backend -c "ruff check apps config tests && ruff format --check apps config tests"
	cd frontend && npm run lint && npm run typecheck
check: lint test
seed:          ## (Re)crée les données de démonstration
	docker compose exec backend python manage.py seed_demo
shell:         ## Shell Django
	docker compose exec backend python manage.py shell

# --- Déploiement Kubernetes -----------------------------------------------------------------
k8s-install: k8s-namespace k8s-pull-secret k8s-secrets k8s-deploy ## Installation complète sur le cluster

k8s-namespace: ## Crée le namespace
	$(KUBECTL) apply -f deploy/k8s/base/namespace.yaml

k8s-pull-secret: ## Recopie le secret de pull GHCR depuis le namespace $(PULL_SECRET_SOURCE_NS)
	@$(KUBECTL) -n $(PULL_SECRET_SOURCE_NS) get secret ghcr-pull-secret -o jsonpath='{.data.\.dockerconfigjson}' | base64 -d > /tmp/.dockerconfigjson
	@$(KN) create secret generic ghcr-pull-secret --type=kubernetes.io/dockerconfigjson --from-file=.dockerconfigjson=/tmp/.dockerconfigjson --dry-run=client -o yaml | $(KN) apply -f -
	@rm -f /tmp/.dockerconfigjson

k8s-secrets:   ## Crée / met à jour les secrets applicatifs depuis $(SECRET_ENV) (voir secret.env.example)
	@test -f $(SECRET_ENV) || { echo "Fichier $(SECRET_ENV) manquant : copier deploy/k8s/secret.env.example"; exit 1; }
	@$(KN) create secret generic app-secrets --from-env-file=$(SECRET_ENV) --dry-run=client -o yaml | $(KN) apply -f -
	@$(KN) create secret generic mailpit-auth --from-literal=users="$$(htpasswd -nbB "$$(grep ^MAILPIT_USER= $(SECRET_ENV) | cut -d= -f2-)" "$$(grep ^MAILPIT_PASSWORD= $(SECRET_ENV) | cut -d= -f2-)")" --dry-run=client -o yaml | $(KN) apply -f -

k8s-deploy:    ## Déploie les manifestes avec les images $(REGISTRY)/*:$(TAG)
	$(KUBECTL) apply -k deploy/k8s/overlays/vps
	$(KN) set image deployment/backend backend=$(REGISTRY)/demo-attestations-backend:$(TAG)
	$(KN) set image deployment/frontend frontend=$(REGISTRY)/demo-attestations-frontend:$(TAG)
	$(KN) rollout status statefulset/postgres --timeout=180s
	$(KN) rollout status deployment/mailpit --timeout=120s
	$(KN) rollout status deployment/backend --timeout=600s
	$(KN) rollout status deployment/frontend --timeout=180s

k8s-restart:   ## Redémarre backend et frontend (récupère les images latest reconstruites)
	$(KN) rollout restart deployment/backend deployment/frontend
	$(KN) rollout status deployment/backend --timeout=600s
	$(KN) rollout status deployment/frontend --timeout=180s

k8s-status:    ## État des pods, volumes, certificat et route
	$(KN) get pods,pvc,svc,certificate,ingressroute

k8s-logs:      ## Logs du backend
	$(KN) logs deployment/backend -f --tail=200

k8s-shell:     ## Shell Django dans le pod backend
	$(KN) exec -it deployment/backend -- python manage.py shell

k8s-seed:      ## (Re)crée les données de démonstration sur le cluster
	$(KN) exec deployment/backend -- python manage.py seed_demo

k8s-certificate: ## Détail du certificat Let's Encrypt
	$(KN) describe certificate demo-axa-tls | tail -20

k8s-mailpit:   ## Accès local à Mailpit sans passer par Internet (http://localhost:8025/mailpit/)
	$(KN) port-forward svc/mailpit 8025:8025

k8s-destroy:   ## Supprime le namespace et toutes ses données
	@read -p "Supprimer le namespace $(NAMESPACE) et ses volumes ? [o/N] " r && [ "$$r" = "o" ]
	$(KUBECTL) delete namespace $(NAMESPACE)
