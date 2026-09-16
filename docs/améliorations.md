# Améliorations digitales – feuille de route proposée

Ce document propose des évolutions pertinentes pour la plateforme d'attestations de chantier, au-delà du périmètre
du test technique. Elles sont classées par horizon et rattachées à un besoin métier concret : fluidifier le
parcours du distributeur, sécuriser la décision du siège, fiabiliser le document remis au maître d'ouvrage et
réduire le coût de traitement. Chaque proposition indique ce qui existe déjà dans la plateforme et sur quoi elle
s'appuie.

## Synthèse

| Horizon | Thème | Proposition phare | Valeur attendue |
|---|---|---|---|
| Court terme (3-6 mois) | Fiabilité des données | Pré-remplissage de l'assuré depuis l'API Sirene (INSEE) | Zéro ressaisie, SIRET et adresse toujours justes |
| Court terme | Qualité documentaire | Analyse de cohérence par un vrai LLM en complément des contrôles déterministes | Détection des incohérences sémantiques, pas seulement lexicales |
| Court terme | Confiance | QR code et page publique de vérification de l'authenticité d'une attestation | Lutte contre les fausses attestations sur les chantiers |
| Moyen terme (6-12 mois) | Instruction | Lecture automatique des pièces (OCR + extraction) et rapprochement avec le FDR | Instruction du siège divisée par deux |
| Moyen terme | Signature | Signature électronique qualifiée (eIDAS) de l'attestation définitive | Valeur probante, fin des signatures scannées |
| Moyen terme | Pilotage | Scoring prédictif entraîné sur l'historique et sinistralité | Priorisation des dossiers à risque réel |
| Long terme (12-24 mois) | Écosystème | API partenaires et portail maître d'ouvrage / plateformes BTP | L'attestation circule là où elle est exigée |
| Long terme | Agents | Assistant conversationnel d'instruction pour le siège et le distributeur | Le dossier se constitue en dialogue, pas en formulaire |

---

## 1. Court terme : fiabiliser et accélérer

### 1.1 Identification de l'assuré par l'API Sirene

* **Existant** : le FDR demande raison sociale, adresse, code postal, ville et SIRET (contrôle de clé de Luhn).
* **Proposition** : à la saisie du SIRET, interroger l'API Sirene de l'INSEE pour pré-remplir raison sociale,
  adresse, code NAF et état administratif de l'établissement. Alerter si l'établissement est fermé ou si le
  code NAF est sans rapport avec les activités déclarées au contrat.
* **Mise en œuvre** : un endpoint backend `GET /referentiels/etablissements/{siret}/` qui appelle l'API avec un
  cache de 24 h, afin de ne jamais exposer la clé d'API au navigateur. Le champ SIRET du formulaire devient un
  champ de recherche avec suggestions.
* **Valeur** : suppression des fautes de frappe, cohérence avec les registres officiels, contrôle de l'existence
  légale de l'assuré au moment de l'attestation.

### 1.2 Analyse de cohérence hybride : règles déterministes + LLM

* **Existant** : `analyse_ia.py` exécute des contrôles déterministes (identité, dates, montants, garanties hors
  périmètre, mentions obligatoires) et produit un JSON structuré avec surlignage dans l'éditeur.
* **Proposition** : conserver ces contrôles comme socle explicable et ajouter un second passage par un modèle de
  langage qui reçoit le FDR, le texte de l'attestation et la liste des contrôles déjà effectués. Le modèle est
  contraint à répondre dans le même schéma JSON (code, sévérité, extrait, explication), ce qui ne change rien au
  frontend. Il détecte ce que les regex ne voient pas : une activité décrite différemment mais équivalente, une
  formulation qui étend implicitement la garantie, un chantier hors France métropolitaine mentionné en toutes
  lettres.
* **Garde-fous** : le modèle ne peut que signaler, jamais valider. Chaque signalement cite un extrait exact que
  l'interface surligne. Les prompts et réponses sont journalisés pour audit. Aucune donnée n'est utilisée pour
  l'entraînement (contrat fournisseur ou modèle hébergé en interne).
* **Valeur** : score de cohérence plus juste, moins de forçages justifiés, explicabilité conservée.

### 1.3 Vérification d'authenticité par QR code

* **Existant** : l'attestation définitive est numérotée (ATT-AAAA-NNNNNN), figée et son PDF est archivé.
* **Proposition** : imprimer sur chaque attestation un QR code menant à une page publique de vérification qui
  affiche uniquement les informations non sensibles : numéro, assuré, période de validité, statut (valide,
  expirée, annulée) et empreinte du PDF. Un maître d'ouvrage ou un coordinateur SPS peut ainsi contrôler une
  attestation sur le chantier depuis son téléphone.
* **Mise en œuvre** : jeton de vérification aléatoire distinct du numéro (pour empêcher l'énumération), page sans
  authentification à débit limité, empreinte SHA-256 du PDF déjà calculable côté serveur.
* **Valeur** : réduction du risque de fausses attestations, dont le coût est porté par l'assureur lors des
  sinistres.

### 1.4 Notifications multicanales et rappels intelligents

* **Existant** : notifications in-app et emails avec lien direct vers l'écran concerné.
* **Proposition** : ajouter les notifications push web (PWA) et un canal SMS pour les événements bloquants
  (compléments demandés, attestation disponible), avec préférences par utilisateur. Compléter par des rappels
  automatiques : projet d'attestation non soumis 5 jours après acceptation, demande en instruction depuis plus de
  48 h côté siège, attestation expirant dans 30 jours.
* **Valeur** : moins de relances manuelles, délais de traitement raccourcis et mesurables dans le reporting.

### 1.5 Application installable et mode dégradé

* **Proposition** : transformer le frontend en Progressive Web App (manifeste, service worker) pour l'installer
  sur mobile et tablette. Les distributeurs saisissent souvent en agence ou en déplacement : la saisie du FDR et
  le dépôt de pièces (photo du devis prise avec l'appareil) doivent fonctionner avec une connexion instable, avec
  synchronisation différée des brouillons.
* **Valeur** : parcours mobile complet pour les agents généraux et courtiers itinérants.

---

## 2. Moyen terme : automatiser l'instruction

### 2.1 Lecture automatique des pièces justificatives

* **Existant** : catalogue de 12 types de pièces, règles d'exigence selon le FDR, contrôle MIME et déduplication.
* **Proposition** : à chaque dépôt, extraire le texte (OCR pour les scans, extraction native pour les PDF) puis
  reconnaître les données clés avec un modèle de document : montant du devis, dates du planning, nom du maître
  d'ouvrage, adresse du chantier, mentions du contrat de sous-traitance. Rapprocher automatiquement ces données du
  FDR et signaler les écarts au distributeur avant l'envoi, puis au siège dans l'écran de traitement.
* **Mise en œuvre** : traitement asynchrone (file de tâches Celery ou Django Tasks), résultat stocké par pièce,
  indicateurs d'écart intégrés au scoring de risque.
* **Valeur** : le siège ne relit plus chaque devis pour vérifier le coût total ; il voit directement « devis à
  612 000 € pour un coût déclaré de 650 000 € : écart 6 % ».

### 2.2 Signature électronique et cachet de l'assureur

* **Existant** : signataire et titre imprimés, validation tracée par le siège.
* **Proposition** : signer électroniquement le PDF de l'attestation définitive avec un cachet électronique
  qualifié de l'assureur (règlement eIDAS), horodatage qualifié inclus. Le document devient vérifiable dans tout
  lecteur PDF, indépendamment de la plateforme.
* **Mise en œuvre** : intégration d'un prestataire de confiance qualifié ou d'un HSM interne, signature appliquée
  lors de la validation, empreinte du document signé archivée avec l'attestation.
* **Valeur** : valeur probante en cas de litige, conformité avec les exigences des marchés publics.

### 2.3 Scoring prédictif

* **Existant** : grille de scoring déterministe et explicable (indicateurs, planchers, synthèse).
* **Proposition** : conserver la grille comme référence réglementaire et lui adjoindre un modèle statistique
  entraîné sur l'historique des demandes, des décisions et, à terme, de la sinistralité par type de chantier,
  activité et zone géographique. Le modèle propose une priorité d'instruction et met en avant les facteurs qui
  pèsent le plus (valeurs SHAP présentées comme des indicateurs supplémentaires).
* **Garde-fous** : pas de décision automatique, surveillance des biais (zone, taille d'entreprise), revue
  périodique par les souscripteurs.
* **Valeur** : les dossiers réellement risqués remontent en tête de file ; les dossiers simples peuvent suivre un
  circuit accéléré.

### 2.4 Circuit accéléré pour les dossiers simples

* **Proposition** : lorsque le score est faible, que toutes les pièces sont lues sans écart et que l'analyse de
  cohérence est propre, proposer au siège une validation en un clic depuis la notification, voire une
  pré-validation automatique confirmée a posteriori par échantillonnage. Les critères d'éligibilité sont
  paramétrables et journalisés.
* **Valeur** : concentrer le temps des souscripteurs sur les 20 % de dossiers qui le méritent.

### 2.5 Gestion du cycle de vie de l'attestation

* **Proposition** : gérer les événements postérieurs à l'émission : renouvellement annuel automatique proposé au
  distributeur avant expiration, avenant lorsque le chantier change (coût, période, activité), annulation en cas de
  résiliation du contrat avec mise à jour de la page de vérification. Historique complet des versions par chantier.
* **Valeur** : l'attestation devient un objet vivant, aligné en permanence sur le contrat.

### 2.6 Espace de paramétrage fonctionnel

* **Existant** : seuils, produits, plafonds, signataire et tableau de garanties définis dans la configuration.
* **Proposition** : écran d'administration pour le siège permettant de gérer sans déploiement les produits, les
  gabarits d'attestation par produit (versionnés, avec prévisualisation), le tableau de garanties, les règles de
  pièces et la grille de scoring. Chaque modification est datée et attribuée ; les attestations déjà émises
  conservent leur version de gabarit.
* **Valeur** : autonomie des équipes métier, traçabilité des règles appliquées à chaque dossier.

---

## 3. Long terme : ouvrir la plateforme

### 3.1 API partenaires et portail maître d'ouvrage

* **Proposition** : exposer une API publique documentée (OAuth 2 client credentials, quotas) permettant aux
  plateformes de gestion de chantier, aux logiciels de courtage et aux maîtres d'ouvrage de demander, recevoir et
  vérifier des attestations. Un portail maître d'ouvrage permettrait de demander à un sous-traitant de fournir son
  attestation directement depuis la plateforme, avec suivi du statut.
* **Valeur** : l'attestation arrive là où elle est exigée, sans pièce jointe qui circule par email.

### 3.2 Portefeuille numérique de l'entreprise assurée

* **Proposition** : espace de consultation pour l'assuré (l'entreprise de bâtiment) regroupant ses attestations
  en cours, leurs dates d'expiration et un partage sécurisé par lien à durée limitée. Compatible avec un futur
  portefeuille d'identité numérique européen pour les justificatifs d'entreprise.
* **Valeur** : l'assuré cesse de solliciter son agent pour réobtenir un document déjà émis.

### 3.3 Assistant d'instruction conversationnel

* **Proposition** : un assistant, disponible pour le distributeur et le siège, capable de répondre sur un dossier
  (« quelles pièces manquent et pourquoi ? », « ce chantier est-il dans les limites du contrat ? »), de rédiger un
  message de demande de compléments à partir des écarts détectés, et de constituer un FDR à partir d'un devis
  déposé. L'assistant agit uniquement au travers des mêmes services et permissions que l'interface : il ne peut
  rien faire qu'un utilisateur ne pourrait faire lui-même.
* **Garde-fous** : réponses sourcées sur les données du dossier et les règles paramétrées, journal des actions,
  validation humaine de toute action à effet (envoi, décision).
* **Valeur** : le dossier se construit en dialogue, l'expertise métier est disponible à toute heure.

### 3.4 Observabilité et exploitation

* **Proposition** : journal d'audit immuable (append-only, horodaté) pour toute décision et toute émission,
  tableaux de bord d'exploitation (délais par étape, taux de compléments, causes de refus), traces distribuées et
  alertes sur les files de traitement. Anonymisation des données personnelles dans les environnements de recette.
* **Valeur** : conformité (RGPD, exigences de contrôle interne) et amélioration continue fondée sur des mesures.

### 3.5 Accessibilité et inclusion

* **Existant** : composants avec attributs ARIA, contrastes issus de la charte, parcours au clavier.
* **Proposition** : audit RGAA complet, mode contraste élevé, lecture vocale des étapes, formulaires
  compatibles avec les lecteurs d'écran sur l'éditeur riche, et version « facile à lire » des courriers envoyés
  aux assurés.
* **Valeur** : conformité réglementaire pour un service numérique d'un grand groupe et meilleure expérience pour
  tous les utilisateurs.

---

## 4. Ordre de mise en œuvre recommandé

1. **API Sirene + QR code de vérification** : faible coût, effet immédiat sur la qualité et la confiance.
2. **Analyse hybride avec LLM** : le contrat d'interface JSON existe déjà, l'intégration est isolée dans un
   service.
3. **Lecture automatique des pièces** : pose l'infrastructure asynchrone réutilisée ensuite par le scoring
   prédictif et l'assistant.
4. **Signature électronique** et **paramétrage fonctionnel** : prérequis pour une mise en production réelle.
5. **API partenaires, portefeuille assuré, assistant** : ouverture de la plateforme une fois le cœur stabilisé.

Chaque étape conserve le principe qui structure déjà le code : les règles métier vivent côté serveur, restent
explicables, et l'humain garde la décision.
