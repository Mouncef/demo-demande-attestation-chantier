# Sécurité

## Authentification et sessions
* JWT (SimpleJWT) : access **30 min**, refresh **7 jours**, **rotation** à chaque refresh et **liste noire** de
  l'ancien token ; déconnexion = révocation du refresh. Tokens portés en en-tête `Authorization` (jamais en
  cookie → aucune surface CSRF) et stockés en `sessionStorage` (fermeture de l'onglet = fin de session).
* Mots de passe : **Argon2** (puis PBKDF2 en secours), validateurs Django (longueur ≥ 12, similarité, mots de
  passe courants).
* Comptes désactivés rejetés à chaque requête (401) même avec un access token valide
  (`apps/core/authentication.py`).
* Throttling DRF : login 10/min par IP (anti force brute), uploads 60/h, analyse IA 30/h, global 1000/h.

## Autorisation
* Permissions par rôle (`EstDistributeur`, `EstSiege`) **et** isolation par requête : un distributeur n'accède
  qu'à ses demandes ; les ressources d'autrui renvoient **404** (pas d'énumération, UUID v4 partout).
* Le propriétaire d'une demande est toujours `request.user` à la création, jamais lu du payload.
* Contrôles d'état dans les services (409) ; `SELECT … FOR UPDATE` pour sérialiser les transitions
  concurrentes ; verrou optimiste (`version`) sur le FDR.

## Pièces jointes
* Liste blanche : PDF, JPEG, PNG (formats Office désactivés par défaut).
* Triple vérification : extension, `Content-Type` déclaré, **type réel détecté par libmagic** sur le contenu.
* Validation structurelle : Pillow (`verify()` + limite 10 000 px/côté contre les bombes de décompression),
  pypdf (rejet des PDF chiffrés, contenant `/JavaScript`, `/OpenAction`, `/AA`).
* Limites : 10 Mo par fichier (413), 20 pièces et 100 Mo par demande, empreinte SHA-256 anti-doublon (par type de pièce : un même document peut servir à plusieurs types).
* Nom de fichier **aléatoire** (`demandes/<uuid>/<uuid>.<ext>`) : le nom d'origine n'entre jamais dans le
  chemin ; stockage hors webroot (`/data/media`), aucune route statique.
* Téléchargement uniquement via endpoint authentifié : vérification `is_relative_to(MEDIA_ROOT)`,
  `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`.
* Suppression logique (historique des soumissions préservé) ; purge physique avec la demande.
* Point d'extension antivirus (ClamAV) documenté dans les améliorations.

## Contenu de l'éditeur riche
* HTML **sanitisé côté serveur** avec `nh3` (liste blanche de balises et d'attributs, pas de liens, images ni
  scripts) avant stockage, rendu PDF et prévisualisation.
* Prévisualisation servie avec `Content-Security-Policy: default-src 'none'` et affichée dans une iframe
  `sandbox`.
* Rendu PDF WeasyPrint avec fetcher restreint aux URI `data:` (pas de SSRF ni d'exfiltration).

## Transport et en-têtes
* nginx : CSP stricte, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`,
  `client_max_body_size` aligné sur la limite d'upload.
* Django (prod) : `SECURE_PROXY_SSL_HEADER`, HSTS, redirection HTTPS paramétrable, `DEBUG=False`,
  `SECRET_KEY` et `ALLOWED_HOSTS` obligatoirement fournis par l'environnement.
* CORS limité aux origines configurées.

## Conteneurs et déploiement
* Images multi-étapes, exécution **non-root** (backend `app`, frontend `nginx-unprivileged`), `readOnlyRootFilesystem`
  et `capabilities: drop ALL` en Kubernetes, namespace en Pod Security « restricted », NetworkPolicy
  (frontend → backend → base uniquement), secrets via `Secret` / gestionnaire externe, jamais dans les images.
* Healthchecks (`/health/` vérifie la base) pour Docker et les probes Kubernetes.

## Journalisation et audit
* Journal d'audit métier `HistoriqueTransition` (qui, quand, de → vers, commentaire, décision, forçage IA).
* Logger `securite` pour les tentatives d'upload malveillant et les accès hors périmètre.
* Réponses d'erreur génériques en cas d'exception non gérée (pas de fuite de trace).
