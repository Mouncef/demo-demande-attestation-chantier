# Charte graphique AXA appliquée à l'application

Source : AXA Brand Hub – Brand Guidelines (Design principles : Colour, Typography, The Switch, Logo),
https://brandhub.axa.com/guidelines/guide/fd7040f0-e4dd-4320-a8b7-1c18965b2866. Le portail digital
(designsystem.axa.com, « One Design System ») est privé : les composants ci-dessous appliquent les principes de la
charte de marque publique.

## Couleurs

| Palette | Nom | Hex | Usage dans l'application |
|---|---|---|---|
| Core | AXA Blue (B) | `#00008F` | titres, boutons primaires, en-têtes de section, liens |
| Core | AXA White (W) | `#FFFFFF` | en-tête, cartes, formulaires |
| Core | AXA Red (R) | `#FF1721` | accent uniquement : Switch, soulignement actif, pastille ; **jamais en fond** |
| Tints | Red Tint 1 | `#FFEAEA` | fond des états « danger », champs invalides, surlignage majeur |
| Tints | Red Tint 2 | `#FF4E56` | jauge (zone élevée), filet de surlignage moyen |
| Tints | Red Tint 3 | `#750707` | texte et contour des actions destructives, niveau de risque élevé (fond, texte blanc) |
| Tints | Blue Tint 1 | `#E2EFFF` | fonds discrets : en-têtes de tableau, informations, chips de variables, survols |
| Tints | Blue Tint 2 | `#6574F8` | focus, bordures actives, rampe ordinale (étape 1) |
| Tints | Blue Tint 3 | `#0C0E45` | texte secondaire, survol des boutons, toasts, rampe ordinale (étape 3) |
| Tints | Light grey | `#E6E6E6` | fond de page, bordures, brouillons (graphiques) |
| Tints | Dark grey | `#999999` | éléments non essentiels (placeholders, pieds de page, axes) |
| Tints | Black | `#0E0E0E` | texte courant |
| Data | Leaf | `#58C645` | états « succès » (texte bleu), série « Acceptées » |
| Data | Sunshine | `#FFF06C` | états « avertissement » (texte bleu), jauge (zone modérée) |
| Data | Grape | `#614FE8` | série « En instruction », série unique des barres |
| Data | Cherry | `#A30245` | série « Refusées » |
| Data | Cotton Candy, Coral, Mint, Sky, Teal | – | disponibles pour de futures infographies |

Combinaisons fond → texte autorisées par la charte (AA / AAA) et utilisées : B→W, W→B/BT3/BLK, BT1→B, BT3→W,
RT1→RT3, RT3→W, LG→B, DG→B, Leaf→B, Sunshine→B, Cherry→W. La Data palette n'est jamais utilisée en fond de page, ni
pour des titres ou du texte courant ; aucun dégradé n'est créé (la jauge de risque est segmentée).

Les tokens sont définis dans `frontend/src/design-system/tokens.css` (couche « marque » puis couche « rôles » :
surfaces, texte, états). Les anciens noms (`--axa-gray-700`, `--axa-orange`…) sont des alias vers ces valeurs.

Palette des graphiques (`frontend/src/features/reporting/palette.ts`) validée par un contrôle de séparation des
couleurs (vision normale et daltonisme) et de contraste : Leaf / Grape / Cherry en ordre adjacent (toutes vérifications OK, Leaf sous 3:1 compensé par les
libellés directs et la vue tableau) ; rampe ordinale Blue Tint 2 → AXA Blue → Blue Tint 3.

## Typographie

| Rôle | Charte | Application |
|---|---|---|
| Titres (h1, h2) | Publico Headline Light | `"Publico Headline", "Source Serif 4"` graisse 300 |
| Titres (h3, h4), mises en avant | Publico Headline Bold | même famille, graisse 700 |
| Texte, boutons, identifiants, annotations | Source Sans Regular / Semibold | `"Source Sans 3"` 400 / 600 |

Publico Headline est une police sous licence (Commercial Type) : elle est déclarée en premier et s'applique
automatiquement si elle est installée ; Source Serif 4 (Google Fonts, libre) en est le substitut. Règles
appliquées : pas de capitales dans les titres, jamais d'italique (`em`/`i` rendus en semi-gras), texte aligné à
gauche, aucun interlettrage personnalisé. Les PDF utilisent les mêmes familles avec repli DejaVu Serif /
Liberation Sans (polices embarquées dans l'image).

Exception documentaire : l'attestation d'assurance reproduit le **format officiel AXA France** (modèle
`attestation-assurance-chantier.pdf`) – titre « ATTESTATION D’ASSURANCE » en capitales, sections en Source Sans
gras bleu, tableau de garanties à en-têtes bleu AXA et sous-en-têtes Blue Tint 1, accroche « réinventons / notre
métier » avec barre rouge – dans l'éditeur comme dans le PDF.

## Le Switch et le logo

* **Hero Switch** sur l'écran de connexion : diagonale rouge centrée dans le panneau bleu, ≥ 50 % de la hauteur,
  trois coins visibles, une seule occurrence.
* **Mini Switch** dans l'en-tête de l'application (signal de navigation), une seule occurrence par écran ; le lien
  actif est souligné en AXA Red.
* Logo officiel (`frontend/public/logo.png`) sur fond blanc (en-tête, PDF, emails) ou bleu (connexion), jamais
  déformé, avec zone de protection.

## Composants

* Boutons : primaire bleu (survol Blue Tint 3), secondaire contour bleu, destructif contour + texte Red Tint 3
  (survol Red Tint 1), angles droits, focus Blue Tint 2.
* Badges d'état : succès Leaf/B, avertissement Sunshine/B, danger RT1/RT3, élevé RT3/W, information BT1/B,
  neutre LG/B, marque B/W ; libellés en minuscules avec majuscule initiale.
* Alertes : fond de l'état, filet gauche bleu (ou Red Tint 3 pour le danger), texte de l'état.
* Tableaux : en-têtes Blue Tint 1 / bleu ; cartes blanches avec filet supérieur bleu ; page sur Light grey.
