# Architecture

## Vue d'ensemble

```
┌──────────────┐   HTTPS    ┌─────────────────────┐   /api,/admin   ┌──────────────────┐        ┌────────────┐
│ Navigateur   │ ─────────► │ frontend (nginx)    │ ──────────────► │ backend (Django)  │ ─────► │ PostgreSQL │
│ React SPA    │            │ build Vite + proxy  │                 │ DRF + WeasyPrint  │        └────────────┘
└──────────────┘            └─────────────────────┘                 │                   │ ─────► SMTP (Mailpit)
                                                                    └───────┬───────────┘
                                                                            └──► /data/media (pièces, PDF – privé)
```

## Backend (Django 5.2 + DRF)

* `config/settings/` : `base.py` (tout par variables d'environnement, paramètres métier `METIER`), `dev.py`,
  `prod.py` (durcissement), `test.py` (rapide, emails en mémoire).
* Couches : **vues DRF** (HTTP, sérialisation, permissions par rôle, isolation par queryset) → **services**
  (règles métier pures, transactions, verrous) → **modèles** (contraintes en base).
* Apps :
  * `core` : modèles abstraits (UUID, horodatage), exceptions métier et handler normalisé, permissions,
    throttling, authentification JWT stricte, sonde `/health/`, commande `seed_demo`.
  * `comptes` : `User` (email + rôle), endpoints `/auth/*`.
  * `demandes` : `Demande`, `FDR`, `SoumissionFDR` (snapshots), `HistoriqueTransition`, `Relance`,
    `CompteurReference` (références lisibles) ; services `workflow`, `exigences`, `scoring`, `relance`,
    `reporting` ; serializer FDR bimode ; filtres.
  * `pieces` : catalogue (constantes + migration de données), `PieceJointe`, validateurs de sécurité, vues
    d'upload / téléchargement.
  * `attestations` : `Attestation` (projet / définitive), `AnalyseIA` ; services `gabarit` (variables, chips),
    `sanitize` (nh3), `analyse_ia` (contrôles), `cycle` (enregistrement, validation, PDF).
  * `documents` : rendu PDF WeasyPrint sans réseau ; `notifications` : modèle + service `emettre` + emails.
* Documentation OpenAPI générée par drf-spectacular (`/api/docs/`, `/api/schema/`).

## Frontend (React 19 + TypeScript)

* `api/` : client axios (JWT, refresh automatique, erreurs normalisées, téléchargement de fichiers), hooks
  TanStack Query par ressource, types miroir de l'API.
* `design-system/` : tokens AXA + composants (Button, Badge, Card, Field/Input/Select/Segmented/OuiNon, Modal,
  Toast, Alert, Stepper, Tabs, Gauge, Pagination, Kpi).
* `features/` :
  * `auth` (contexte, page de connexion), `demandes` (liste + filtres, détail en stepper / vue siège, relance),
  * `fdr` (schéma zod, règles de pièces client, formulaire dynamique), `pieces` (scoring, checklist, dropzone),
  * `validation` (récapitulatif, envoi), `siege` (instruction), `attestation` (éditeur TipTap, nœud `variable`,
    extension de surlignage, panneau IA), `notifications`, `reporting` (Recharts 3 chargé à la demande : `palette.ts`
    validée pour le daltonisme et le contraste, `ChartCard` avec vue tableau, graphiques `charts/*`).
* Le backend reste la source de vérité : le front rejoue seulement les règles d'affichage (pièces qui seront
  requises) et masque les actions selon `actions_possibles`.

## Flux principaux

1. **Saisie** : `PATCH /fdr/` à chaque enregistrement (verrou `version`) → réponse = FDR normalisé.
2. **Complétude** : `GET /completude/` (exigences + validité FDR) et `GET /scoring/` recalculés à la volée.
3. **Envoi** : `POST /envoyer/` → transaction : validation, complétude, snapshot, PDF, historique, notifications
   (email après commit).
4. **Instruction** : actions siège → transitions ; `A_COMPLETER` rend la main au distributeur.
5. **Attestation** : `GET /gabarit/` (contenu, variables, cadre et feuille de style du document) → éditeur →
   `PUT` (sanitisation) → `POST /analyser/` (contrôles, extraits) → `POST /valider/` (empreinte vérifiée) → PDF,
   numéro, notification. L'aperçu (`POST /previsualiser/?sortie=pdf`) est le PDF lui-même, produit par le même
   moteur et le même gabarit que l'export ; la feuille de l'éditeur reprend le markup et la feuille de style
   `templates/pdf/attestation.css` du PDF (mêmes polices installées dans l'image), et les documents en lecture
   seule (projet soumis, définitive validée) affichent directement le fichier enregistré.

## Données persistées

Voir `backend/apps/*/models.py`. Points notables : contraintes `CHECK` (dates, montants, décision seulement si
traitée), index sur statut / décision / notifications non lues, unicité (demande, kind) des attestations,
JSONB pour les snapshots et résultats d'analyse.
