# Règles métier

Référence fonctionnelle de la plateforme. Le code source de référence est indiqué pour chaque règle.

## 1. Machine à états (`backend/apps/demandes/services/workflow.py`)

```
création (DISTRIBUTEUR) ─────────────────────────────► BROUILLON
BROUILLON ──envoyer (FDR valide + dossier complet)───► EN_COURS
EN_COURS ──demander compléments (SIEGE, message ≥ 10)─► A_COMPLETER ──renvoyer (DISTRIBUTEUR)──► EN_COURS
EN_COURS ──accepter (SIEGE)──────────────────────────► TRAITE / ACCEPTEE  → attestation DEFINITIVE possible
EN_COURS ──refuser (SIEGE, motif ≥ 10 caractères)────► TRAITE / REFUSEE   (terminal, pas d'attestation définitive)
EN_COURS ──relancer (DISTRIBUTEUR, 1 fois / 24 h)────► (statut inchangé)
BROUILLON jamais envoyé ──supprimer (DISTRIBUTEUR)───► supprimée
```

| Transition | Rôle | Préconditions (sinon) | Effets |
|---|---|---|---|
| Sauvegarder le FDR | propriétaire | statut BROUILLON / A_COMPLETER (409), `version` concordante (409 `CONFLIT_VERSION`), validation brouillon (400) | FDR mis à jour et normalisé, `version += 1` |
| Envoyer / renvoyer | propriétaire | statut BROUILLON / A_COMPLETER (409), FDR valide en mode envoi (400 par champ), dossier complet (409 `DOSSIER_INCOMPLET` + `manquants`) | `EN_COURS`, `nb_soumissions += 1`, snapshot (FDR, pièces, scoring) + PDF FDR, notification + email au siège |
| Demander compléments | SIEGE | EN_COURS (409), message ≥ 10 caractères (400) | `A_COMPLETER`, notification + email au distributeur |
| Accepter | SIEGE | EN_COURS (409) | `TRAITE` / `ACCEPTEE`, notification + email |
| Refuser | SIEGE | EN_COURS (409), motif ≥ 10 caractères (400) | `TRAITE` / `REFUSEE`, notification + email avec motif |
| Relancer | propriétaire | EN_COURS (409), délai 24 h écoulé (429 + `Retry-After`) | `Relance` enregistrée, email + notification au siège |
| Supprimer | propriétaire | BROUILLON jamais envoyé (409) | suppression physique (FDR, pièces, fichiers) |

Chaque transition verrouille la demande (`SELECT … FOR UPDATE`), journalise dans `HistoriqueTransition` et émet
les notifications après commit. Après `TRAITE`, FDR, pièces et commentaires sont figés.

## 2. Droits et codes HTTP (`backend/apps/core/permissions.py`, `get_queryset`)

* **401** non authentifié ou compte désactivé · **403** rôle non autorisé · **404** ressource inexistante *ou non
  visible* (un distributeur ne voit que ses demandes : l'existence des autres n'est pas révélée) · **409** action
  incompatible avec l'état · **400** validation · **413/415** fichier · **429** relance trop tôt / throttling.

| Action | Distributeur propriétaire | Autre distributeur | Siège |
|---|---|---|---|
| Créer une demande | ✅ | – | 403 |
| Lire / lister | ✅ (les siennes) | 404 | ✅ (toutes) |
| Modifier FDR, pièces, envoyer, relancer, supprimer | ✅ selon l'état | 404 | 403 |
| Compléments / accepter / refuser / commentaire siège | 403 | 403 | ✅ si EN_COURS |
| Projet d'attestation (créer, éditer, soumettre, reprendre) | ✅ si acceptée et définitive non établie | 404 | lecture seule ; demander une correction |
| Attestation définitive (créer, éditer, valider) | lecture / PDF **uniquement si validée** (404 sinon) | 404 | ✅ si TRAITE + ACCEPTEE |
| Analyse IA de cohérence (lancer, consulter) | 403 | 403 | ✅ sur la définitive uniquement |
| Notifications | les siennes | – | les siennes |
| Reporting | ses demandes | – | global |

Le serializer expose `actions_possibles` (calculé serveur) pour piloter l'interface.

## 3. Validation du FDR (`backend/apps/demandes/serializers/fdr.py`)

Deux modes : **brouillon** (tout facultatif, formats et règles croisées seulement si les deux membres sont
renseignés) et **envoi** (obligations complètes).

* Formats : n° de contrat normalisé (majuscules, sans espaces/tirets) `^[A-Z0-9]{6,20}$` ; code postal `^\d{5}$` ;
  SIRET 14 chiffres (espaces de groupement tolérés à la saisie) avec **clé de Luhn** valide ; montants décimaux
  positifs (2 décimales) ; textes nettoyés (caractères de contrôle supprimés).
* Identification de l'assuré (imprimée sur l'attestation) : nom, adresse, code postal, ville et SIRET sont
  obligatoires à l'envoi ; la référence client est facultative (reprise dans « Vos références »).
* Règles croisées : `date_fin ≥ date_debut` ; durée ≤ 10 ans ; à l'envoi `date_debut` ≥ aujourd'hui − 1 an et
  ≤ + 3 ans ; `montant_prestation ≤ cout_total` ; description ≥ 20 caractères à l'envoi.
* Conditionnels : rénovation → `modification_structure` requis ; usage AUTRE → précision (≥ 3) ; activité non
  couverte → précision (≥ 10). Les champs dont la condition n'est plus vraie sont **effacés** à la sauvegarde.
* Seuil « > 10 M€ » strictement supérieur : 10 000 000,00 € exactement ne déclenche aucune pièce.

## 4. Pièces requises et complétude (`backend/apps/demandes/services/exigences.py`, catalogue `apps/pieces/catalogue.py`)

| Code | Libellé | Déclencheur | Niveau |
|---|---|---|---|
| ETUDE_STRUCTURE | Étude / note de calcul structure (BET) | `modification_structure = true` | REQUIS |
| AUTORISATION_URBANISME | Permis de construire / déclaration préalable | `modification_structure = true` | REQUIS |
| DESCRIPTIF_TECHNIQUE | Descriptif technique détaillé | `chantier_atypique = true` | REQUIS |
| PHOTOS_PLANS | Photos du site / plans | `chantier_atypique = true` | REQUIS |
| MARCHE_SIGNE | Devis accepté / marché signé | `cout_total > 10 M€` | REQUIS |
| ATTESTATION_DO | Attestation dommages-ouvrage | `cout_total > 10 M€` | REQUIS |
| PLANNING_PREVISIONNEL | Planning prévisionnel | `cout_total > 10 M€` | REQUIS |
| DESCRIPTIF_ACTIVITE | Descriptif de l'activité hors contrat | `activite_couverte = false` | REQUIS |
| JUSTIFICATIF_QUALIFICATION | Qualification (Qualibat, RGE…) | `activite_couverte = false` | REQUIS |
| AVIS_TECHNIQUE | Avis technique / ATEx | `travaux_standards = false` | REQUIS |
| CONTRAT_SOUS_TRAITANCE | Contrat de sous-traitance | `type_intervention = SOUS_TRAITANT` | RECOMMANDÉ |
| AUTRE | Autre document | jamais requis | – |

**Dossier complet** ⇔ FDR valide en mode envoi **et** chaque exigence REQUISE a ≥ 1 pièce non supprimée. Les
pièces d'un type devenu non requis restent (badge « facultative »). Le type d'une pièce peut être corrigé sans
re-dépôt tant que la demande est éditable. Suppression logique (`deleted_at`).

## 5. Scoring de risque simulé (`backend/apps/demandes/services/scoring.py`)

| Facteur | Points |
|---|---|
| Coût total : < 500 k€ / 500 k–2 M€ / 2–10 M€ / > 10 M€ | 0 / 10 / 20 / 35 |
| Prestation > 1 M€ | +5 |
| Sous-traitant déclarant ≥ 80 % du coût total | +5 |
| Rénovation sans / avec modification de structure | 5 / 25 |
| Chantier atypique | 20 |
| Activité hors contrat | 30 |
| Travaux non standards | 15 |
| Sous-traitance | 10 |
| Durée : ≤ 6 / 6–18 / 18–36 / > 36 mois | 0 / 5 / 10 / 15 |
| Usage : habitation / bureau / commerce / autre | 5 / 0 / 5 / 10 |
| Dossier incomplet | +10 |
| Pièce recommandée absente | +3 |
| Sinistralité simulée (hash du n° de contrat : 0–3 sinistres) | 0 / 5 / 10 / 20 |

`score = min(100, points)` · FAIBLE < 30 ≤ MODÉRÉ < 65 ≤ ÉLEVÉ · planchers : hors contrat ⇒ ≥ MODÉRÉ ; hors
contrat + (atypique ou structure) ⇒ ÉLEVÉ. Synthèse textuelle : niveau, 3 facteurs principaux, complétude,
recommandation. Calcul à la volée, snapshot à chaque envoi.

## 6. Relance (`backend/apps/demandes/services/relance.py`)

Prochaine relance possible = max(`submitted_at + RELANCE_DELAI_INITIAL_HOURS`, `dernière relance + RELANCE_COOLDOWN_HOURS`).
Trop tôt ⇒ 429 `RELANCE_TROP_TOT` avec `prochaine_relance_possible` et en-tête `Retry-After`. Destinataires : boîte
fonctionnelle `SIEGE_MAILBOX` si définie, sinon tous les utilisateurs SIEGE actifs ; copie au distributeur.

## 7. Attestations (`backend/apps/attestations/services/cycle.py`, gabarit `gabarit.py`)

Circuit après **acceptation** de la demande :

```
agent : PROJET EN_EDITION ──soumettre──► SOUMISE ──(siège) demander correction──► A_CORRIGER ──soumettre──► SOUMISE
                                    ▲        │ notif + email SIEGE                     │ notif + email agent
                                    └reprendre┘
siège : DÉFINITIVE (pré-remplie depuis le projet SOUMIS, sinon gabarit AXA) ──rectifie──► analyse IA ──► VALIDEE
                                                                                            │ notif + email agent, numéro ATT-AAAA-NNNNNN, PDF
```

| Transition | Rôle | Préconditions (sinon) | Effets |
|---|---|---|---|
| Créer / modifier le projet | distributeur propriétaire | demande TRAITE + ACCEPTEE (409), définitive non établie (409), projet non SOUMIS (409) | contenu sanitisé, variables rafraîchies |
| Soumettre le projet | distributeur propriétaire | statut EN_EDITION ou A_CORRIGER (409), contenu non vide | `SOUMISE`, `soumise_le`, PDF « PROJET », historique, **notification + email au siège** |
| Reprendre le projet | distributeur propriétaire | statut SOUMISE (409), définitive non établie | `EN_EDITION` (retrait volontaire, pas d'email) |
| Demander une correction | siège | statut SOUMISE (409), commentaire ≥ 10 caractères (400), définitive non établie | `A_CORRIGER` + commentaire, historique, **notification + email au distributeur** |
| Créer / modifier la définitive | siège | demande TRAITE + ACCEPTEE (409), **projet soumis** par le distributeur ou définitive déjà entamée (409 sinon, gabarit compris), non validée (409) | contenu initial = copie du projet soumis ; l'action `editer_attestation_definitive` n'est exposée qu'à partir de la soumission |
| Analyser (IA) | siège | définitive existante | résultat persisté (empreinte du contenu) |
| Valider la définitive | siège | analyse COHÉRENTE et à jour, ou `forcer` + justification ≥ 10 (409 sinon) | `VALIDEE`, numéro, PDF final, **notification + email au distributeur** ; projet figé |

* Le distributeur **ne voit pas** l'attestation définitive (lecture 404, PDF 404, étape absente du parcours)
  tant qu'elle n'est pas validée ; `etat_attestation` reste `AUCUNE` / `PROJET_*` jusque-là, puis `DEFINITIVE`.
  Symétriquement, le siège ne voit l'onglet « Attestation définitive » qu'une fois le projet soumis.
* Zones dynamiques : `<span data-variable="cle">` rafraîchies depuis le FDR à chaque rendu ; HTML sanitisé (nh3).
* **Éditeur WYSIWYG** (`frontend/src/features/attestation/BarreOutils.tsx`) : historique, styles de bloc (titres 1-3,
  citation), police (six familles installées dans l'image), taille en points, interligne, gras / italique /
  souligné / barré / exposant / indice, couleur et surlignage (palette de la charte ou couleur libre), alignement,
  retraits (pas de 5 mm), listes et niveaux, ligne horizontale, tableaux (insertion N×M, lignes, colonnes,
  fusion, scission, ligne d'en-tête, fond de cellule), image PNG / JPEG incorporée (1 Mo, largeur relative),
  lien https, saut de page, caractères spéciaux, date du jour, rechercher / remplacer, compteur de mots,
  zoom, plein écran. Tout ce que l'éditeur produit est accepté par la liste blanche du serveur : balises de mise
  en forme, `mark`, `sub`, `sup`, `img` (`data:image/png|jpeg` uniquement, décodée et vérifiée, 1 Mo), `a`
  (`https` uniquement), attribut `style` **filtré propriété par propriété** (couleurs, police parmi la liste,
  taille 6-72 pt, interligne 1-3, alignement, retraits, largeur, sauts de page ; aucune URL ni expression).
* **Format officiel AXA France** (modèle `attestation-assurance-chantier.pdf`, contrat « BTPlus Concept ») :
  * *Cadre non modifiable* (`templates/pdf/attestation.html`, reproduit dans l'éditeur) : page 1 avec bloc
    « Votre Intermédiaire » (organisation, adresse, téléphone, email du distributeur – profil utilisateur),
    accroche « réinventons / notre métier », logo AXA, étiquettes « Votre contrat » (produit) et « Vos références »
    (n° de contrat, référence client), destinataire (assuré + adresse) et « Date du courrier » ; mentions légales
    AXA France IARD S.A. / AXA Assurances IARD Mutuelle en pied de page 1 ; en-tête courant « Vos références
    Contrat … Client … » et pagination « n/N » sur les pages suivantes ; filigrane PROJET pour le projet.
  * *Corps éditable* (`templates/attestations/corps_gabarit.html`) : titre « ATTESTATION D’ASSURANCE », paragraphe
    d'attestation (assuré, adresse, SIRET, contrat n° et période de validité), bloc « Chantier concerné » (objet de
    la demande), sections **1-** garanties objet de l'attestation (missions, ouverture de chantier, France
    métropolitaine, plafond du coût de construction, travaux/produits/procédés NF DTU – C2P – RAGE – ATE – ATec –
    ATEx, notes (1)(2)(3)), **2-** garantie de responsabilité décennale obligatoire (nature, montant, durée),
    réserve, **3-** autres garanties souscrites (sous-traitant 1792-4-2, réclamations à compter du début de
    période, équipements dissociables 2.5, dommages intermédiaires 2.6, existants 2.7, immatériels, RC 2.10),
    « Activités Garanties » (description des travaux + mention explicite « non garantie » si activité hors
    contrat), « Tableau de garanties » (tableau du modèle : plafonds, franchise, indexation, CCRD), réserve et
    exclusion CMI (loi du 19/12/1990), signature « Fait à Nanterre, le … » avec signataire et titre.
  * *Valeurs par défaut paramétrées* (`METIER["ATTESTATION"]`) : produit, plafond du coût de construction
    (2 000 000 €), lieu de signature, signataire et titre, franchise, plafond d'indexation, mentions légales. La
    **période de validité du contrat** est l'année civile de la date d'édition (1er janvier → 1er janvier suivant).
    Ces valeurs sont des zones dynamiques ou du texte rectifiable par le siège avant validation.
  * Les classes de mise en page du format (`titre-attestation`, `section-droite`, `garanties`, `sous-titre`,
    `note`, `signature`, `chantier`, `bloc-assure`) sont conservées par l'éditeur et autorisées par la sanitisation.

## 8. Analyse de cohérence simulée (`backend/apps/attestations/services/analyse_ia.py`)

Adaptations au format officiel : le **tableau de garanties** est exclu des contrôles de montants et de garanties
hors périmètre (« Protection juridique – non accordée » y figure) ; les montants portés par les zones dynamiques
contractuelles (plafond) et les dates de la période de validité du contrat ou antérieures à 2000 (références
législatives) sont tolérés ; contrôle `SIRET_ABSENT` (moyenne) si le SIRET du FDR n'apparaît pas.

| Code | Sévérité | Contrôle |
|---|---|---|
| ATTESTATION_VIDE | majeure | texte < 50 caractères |
| PLACEHOLDER_NON_REMPLI | majeure | `{{`, « à compléter », `XXX`, `___`, zone dynamique vide |
| ASSURE_ABSENT / CONTRAT_ABSENT | majeure | nom de l'assuré / n° de contrat introuvables |
| CONTRAT_DIFFERENT | majeure | mention « contrat n° X » avec X ≠ FDR |
| CHANTIER_ABSENT / VILLE_CHANTIER_ABSENTE | moyenne | chantier / ville introuvables |
| VILLE_ASSURE_ABSENTE | mineure | ville de l'assuré introuvable |
| DATES_ABSENTES / DATE_INVALIDE / DATE_HORS_FDR | moyenne | aucune date, date impossible (31/02), date étrangère au FDR |
| PERIODE_INCOHERENTE | majeure | « du X au Y » avec Y < X |
| TRAVAUX_ABSENTS | moyenne | < 40 % des mots significatifs de la description repris |
| MONTANT_DIFFERENT | moyenne | montant en € ne correspondant ni au coût total ni à la prestation (± 1 %) |
| GARANTIE_NON_DECLAREE | majeure | dommages-ouvrage, TRC, protection juridique, bris de machine, GFA… |
| ACTIVITE_HORS_CONTRAT | majeure | activité non couverte présentée comme relevant du contrat |
| TYPE_INTERVENTION | moyenne | sous-traitant présenté comme entreprise principale |
| MENTION_RESERVE_ABSENTE / MENTION_DECENNALE_ABSENTE | moyenne | réserve légale / mention décennale absentes |
| DEFINITIVE_MENTION_PROJET | majeure | « projet » ou « provisoire » dans une définitive |

Pénalités 25 / 10 / 3 ; `score = max(0, 100 − Σ)` ; **COHÉRENT** si aucune majeure et score ≥ 80. Chaque
incohérence porte un `extrait` (+ `offset`) utilisé par le frontend pour surligner le passage dans l'éditeur.

## 9. Notifications (`backend/apps/notifications/services.py`)

| Type | Déclencheur | Destinataires |
|---|---|---|
| DEMANDE_ENVOYEE / DEMANDE_RENVOYEE | envoi / renvoi | utilisateurs SIEGE |
| RELANCE | relance | utilisateurs SIEGE (+ copie email au distributeur) |
| COMPLEMENTS_DEMANDES | demande de compléments | distributeur |
| DEMANDE_TRAITEE | acceptation / refus | distributeur |
| PROJET_ATTESTATION_SOUMIS | soumission du projet par le distributeur | utilisateurs SIEGE |
| PROJET_ATTESTATION_A_CORRIGER | renvoi du projet par le siège (avec commentaire) | distributeur |
| ATTESTATION_DISPONIBLE | validation de la définitive | distributeur |

Une ligne par destinataire (statut lu individuel) ; email envoyé après commit, échec journalisé sans bloquer.
