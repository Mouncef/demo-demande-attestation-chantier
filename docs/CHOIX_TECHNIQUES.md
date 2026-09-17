# Choix techniques

Ce document explique les décisions prises pour la plateforme de gestion des demandes d'attestation de chantier :
la pile technique, l'architecture, la modélisation du métier, la sécurité, la qualité et le déploiement. Pour
l'installation, voir le [README](../README.md).

---

## 1. Pile technique

| Couche | Choix | Pourquoi |
|---|---|---|
| Langage backend | Python 3.13 | Écosystème mature pour une application de gestion, lisibilité, outillage de test |
| Framework backend | Django 5.2 LTS + Django REST Framework | ORM, migrations, administration, authentification et permissions intégrées ; DRF apporte serializers, viewsets, filtres et schéma OpenAPI (drf-spectacular). Version LTS pour une maintenance longue |
| Base de données | PostgreSQL 16 | Contraintes `CHECK`, JSONB pour les snapshots et résultats d'analyse, verrous de ligne (`SELECT … FOR UPDATE`) pour sérialiser les transitions |
| Authentification | JWT (SimpleJWT) : access 30 min, refresh 7 jours avec rotation et liste noire | API sans état, adaptée à une SPA ; pas de cookie de session donc pas de CSRF sur l'API ; révocation possible à la déconnexion |
| PDF | WeasyPrint | Rendu PDF depuis les gabarits HTML/CSS Django, sans navigateur headless ; l'aperçu est le PDF lui-même et l'éditeur applique la feuille de style du document avec les mêmes polices, pour un rendu identique à l'écran et dans le fichier |
| Frontend | React 19 + TypeScript 5.9 + Vite | Composants typés, build rapide, typage de bout en bout des réponses de l'API |
| Données côté client | TanStack Query | Cache, invalidation après chaque action, rafraîchissement du compteur de notifications |
| Formulaires | react-hook-form + zod | Formulaire FDR dynamique avec validation déclarative, schéma miroir des règles serveur |
| Éditeur riche | TipTap 3 (ProseMirror) | Nœud personnalisé pour les zones dynamiques, décorations pour le surlignage des incohérences, HTML contrôlé |
| Graphiques | Recharts 3 | Graphiques déclaratifs, chargés à la demande (chunk séparé) pour ne pas alourdir le bundle initial |
| Style | Design system maison conforme à la charte AXA | Pas de bibliothèque UI lourde ; jetons (couleurs, typographie), composants accessibles, palette de données validée pour le daltonisme |
| Conteneurs | Docker multi-étapes, utilisateur non root, nginx non privilégié | Démarrage en une commande sur Linux, Windows et macOS ; images identiques en local et sur le cluster |
| Orchestration | Kustomize, Traefik, cert-manager | Manifestes lisibles sans templating, TLS automatique, réutilisation de l'infrastructure existante du cluster |

## 2. Architecture

```
Navigateur ── HTTPS ──► frontend (nginx : SPA + proxy /api, /admin, /static) ──► backend (Django + DRF)
                                                                                   ├─► PostgreSQL
                                                                                   ├─► SMTP (Mailpit)
                                                                                   └─► /data/media (pièces et PDF, hors webroot)
```

### Backend en trois couches

* **Vues DRF** : HTTP, sérialisation, permissions par rôle, isolation des données par queryset (un distributeur
  ne voit que ses demandes ; une demande d'un autre distributeur renvoie 404 pour ne pas révéler son existence).
* **Services** : règles métier pures et transactions (`workflow`, `exigences`, `scoring`, `relance`,
  `reporting`, `cycle` des attestations, `gabarit`, `analyse_ia`). Les vues ne contiennent pas de règle métier.
* **Modèles** : contraintes en base (dates cohérentes, montants positifs, décision uniquement si traitée),
  index sur les colonnes filtrées, unicité des attestations par demande et par type.

Applications : `core` (socle technique), `comptes`, `demandes`, `pieces`, `attestations`, `documents`,
`notifications`. Chaque application possède ses modèles, services, serializers, vues et tests.

### Frontend par fonctionnalité

`api/` (client axios avec injection du JWT, renouvellement automatique de l'access token, erreurs
normalisées, hooks par ressource, types miroir de l'API), `design-system/` (jetons et composants),
`features/` (auth, demandes, fdr, pieces, validation, siege, attestation, notifications, reporting),
`lib/` (formatage, libellés).

### Le serveur reste la source de vérité

Les actions disponibles sur une demande (`actions_possibles`) et l'état du circuit d'attestation
(`etat_attestation`) sont calculés côté serveur et simplement affichés par l'interface. Le frontend rejoue
seulement les règles d'affichage immédiat (pièces qui seront requises, validation des champs) et le backend
revalide tout à l'envoi.

## 3. Modélisation du métier

### Machine à états de la demande

```
BROUILLON ──envoyer──► EN_COURS ──accepter / refuser──► TRAITE (décision ACCEPTEE ou REFUSEE)
                          │ demander des compléments
                          ▼
                     A_COMPLETER ──renvoyer──► EN_COURS
```

Chaque transition verrouille la ligne, vérifie le statut source (sinon erreur 409), applique les effets,
journalise dans l'historique et émet les notifications après commit. Chaque envoi fige un **snapshot** (FDR,
pièces, scoring) avec le PDF du FDR : le siège instruit sur des données immuables et les envois successifs sont
comparables.

### Formulaire de Déclaration du Risque

Deux modes de validation : **brouillon** (tout facultatif, seuls les formats et les règles croisées renseignées
sont contrôlés) et **envoi** (obligations complètes, champs conditionnels). Formats contrôlés : numéro de
contrat normalisé, code postal, SIRET à 14 chiffres avec clé de Luhn, montants à deux décimales, bornes de
plausibilité des dates. Un verrou optimiste (`version`) empêche d'écraser une modification concurrente.

### Pièces justificatives et règles d'exigence

Catalogue de douze types de pièces (référentiel alimenté par migration de données). Les exigences dérivent du
FDR : modification de structure, chantier atypique, coût supérieur à 10 M€ (strictement), activité hors contrat,
travaux non standards, sous-traitance (recommandé). Le dossier n'est envoyable que lorsque toutes les pièces
requises sont présentes.

### Scoring de risque

Grille déterministe et explicable : chaque indicateur porte des points et un détail, des planchers imposent un
niveau minimal (par exemple activité hors contrat), le niveau final est faible, modéré ou élevé. Le score est
figé à l'envoi pour l'instruction et affiché avec sa décomposition.

### Attestations

Deux documents par demande : le **projet** préparé par le distributeur après acceptation et soumis au siège,
puis la **définitive** établie par le siège à partir du projet, invisible pour le distributeur tant qu'elle n'est
pas validée. Le contenu suit le format officiel AXA France : cadre non modifiable (intermédiaire, références,
destinataire, mentions légales, en-tête courant, pagination) et corps éditable (garanties, activités garanties,
tableau de garanties, signature) dont les **zones dynamiques** sont rafraîchies depuis le FDR à chaque rendu.

L'**analyse de cohérence** est une suite de contrôles déterministes (identité de l'assuré, contrat, SIRET,
dates, montants, garanties hors périmètre, mentions obligatoires, espaces réservés non remplis) qui produit un
résultat structuré (code, sévérité, extrait à surligner, score). Cette interface a été conçue pour être remplacée
par un modèle de langage sans changer le frontend. La validation de la définitive exige une analyse cohérente
portant sur le contenu courant (empreinte du HTML), ou un forçage justifié tracé dans l'historique.

### Notifications et relance

Notifications in-app par destinataire, complétées par un email envoyé après commit dont l'échec n'annule jamais
l'action métier. La relance du siège respecte un délai minimal de 24 h (erreur 429 avec `Retry-After`).

## 4. Sécurité

* **Authentification** : JWT courts avec rotation et liste noire, limitation des tentatives de connexion,
  hachage Argon2, comptes inactifs refusés.
* **Autorisation** : permissions par rôle sur chaque action, isolation par queryset, contrôle d'état dans les
  services (409), actions possibles calculées côté serveur.
* **Pièces jointes** : type réel détecté par libmagic (un exécutable renommé en `.pdf` est refusé), extensions et
  taille bornées, quotas par demande, déduplication par empreinte, fichiers stockés hors webroot et servis
  uniquement par des vues authentifiées, nommage d'après le type de pièce.
* **Éditeur riche** : HTML nettoyé par liste blanche (nh3) : pas de script, de lien ni d'image ; seules les
  balises de mise en forme, les tableaux et les zones dynamiques sont conservés. Prévisualisation servie avec une
  CSP dédiée.
* **PDF** : WeasyPrint sans accès réseau ni système de fichiers (seules les URI `data:` sont autorisées), ce qui
  neutralise les attaques SSRF ou d'exfiltration via du HTML injecté.
* **Transport** : TLS terminé par Traefik avec redirection HTTP vers HTTPS, en-têtes de sécurité (HSTS,
  nosniff, frame deny, Referrer-Policy, Permissions-Policy, CSP stricte sur l'application).
* **Conteneurs** : images non root, système de fichiers en lecture seule pour le backend, capacités abandonnées,
  Pod Security « restricted » sur le namespace, NetworkPolicies (le backend n'accepte que le frontend, la base
  n'accepte que le backend), secrets hors du dépôt.
* **Erreurs** : format homogène `{code, detail}` sans fuite de détails internes ; journalisation des actions
  métier.

## 5. Qualité et outillage

* **Tests backend** (pytest, 80 tests) : validation du FDR, règles d'exigence, scoring, workflow et droits par
  rôle via l'API, relance, pièces (types réels, quotas, droits), attestations (cycle complet, sanitisation, PDF),
  analyse de cohérence, authentification. Les emails sont capturés en mémoire et les callbacks après commit
  exécutés dans les tests.
* **Tests frontend** (vitest, testing-library) : schéma zod, règles de pièces, composants du design system,
  formatage.
* **Lint et typage** : ruff (lint et format, ligne de 120), eslint, prettier, TypeScript strict.
* **Documentation de l'API** : schéma OpenAPI généré, Swagger UI sur `/api/docs/`.
* **Intégration continue** : tests backend avec PostgreSQL de service, tests et build frontend, validation des
  manifestes Kubernetes (kustomize et kubeconform), construction et publication des images sur GHCR avec cache.

## 6. Déploiement

* **Docker Compose** pour le développement et la démonstration locale : quatre services (PostgreSQL, Mailpit,
  backend, frontend), un seul port exposé, migrations et jeu de démonstration au démarrage.
* **Kubernetes** (`deploy/k8s`, Kustomize) : les mêmes quatre services sur le cluster, PostgreSQL en StatefulSet
  avec volume persistant, backend en un réplica avec stratégie `Recreate` (volume média en lecture-écriture
  unique sur un nœud), Mailpit exposé sous `/mailpit` derrière une authentification basique, certificat Let's
  Encrypt automatique. Le déploiement est piloté par `make` (`k8s-install`, `k8s-deploy TAG=…`, `k8s-restart`,
  `k8s-status`) et les images proviennent de GitHub Actions.

## 7. Limites connues et évolutions envisagées

* Les règles métier existent en Python et, pour l'affichage, en TypeScript : une génération de types depuis le
  schéma OpenAPI et un test de cohérence des listes de champs éviteraient toute divergence.
* Le référentiel de garanties du gabarit d'attestation est porté par le template et la configuration : un
  paramétrage en base, éditable par le siège, serait préférable en production.
* L'analyse de cohérence repose sur des contrôles lexicaux : une analyse sémantique par modèle de langage,
  contrainte au même format de sortie, en améliorerait la finesse.
* Le stockage des médias est un volume local : plusieurs réplicas backend demanderaient un stockage partagé ou
  un stockage objet.
* Pistes produit : pré-remplissage de l'assuré via l'API Sirene, QR code de vérification d'authenticité des
  attestations, lecture automatique des pièces, signature électronique, scoring prédictif, API partenaires.
