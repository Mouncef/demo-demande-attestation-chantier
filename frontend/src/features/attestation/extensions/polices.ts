// Référentiels de l'éditeur WYSIWYG : polices, tailles, interlignes, couleurs et caractères spéciaux.
// Les familles de polices sont celles installées dans l'image backend (rendu PDF) et acceptées par le filtre de
// styles du serveur (apps/attestations/services/sanitize.py) : l'écran et le fichier utilisent les mêmes glyphes.

export interface Police {
  libelle: string;
  valeur: string;
}

export const POLICES: Police[] = [
  { libelle: 'Source Sans 3 (charte)', valeur: '"Source Sans 3", Arial, sans-serif' },
  { libelle: 'Source Serif 4 (titres)', valeur: '"Source Serif 4", Georgia, serif' },
  { libelle: 'Liberation Sans (Arial)', valeur: '"Liberation Sans", Arial, sans-serif' },
  { libelle: 'Liberation Serif (Times)', valeur: '"Liberation Serif", "Times New Roman", serif' },
  { libelle: 'Liberation Mono (Courier)', valeur: '"Liberation Mono", "Courier New", monospace' },
  { libelle: 'DejaVu Sans', valeur: '"DejaVu Sans", Arial, sans-serif' },
];

/** Tailles en points, comme sur le document imprimé (le corps du gabarit est en 10 pt). */
export const TAILLES_PT = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 36];

export const INTERLIGNES: { libelle: string; valeur: string }[] = [
  { libelle: 'Simple', valeur: '1' },
  { libelle: '1,15', valeur: '1.15' },
  { libelle: '1,5', valeur: '1.5' },
  { libelle: 'Double', valeur: '2' },
];

/** Palette de la charte AXA (Core, Tints, Data) proposée pour le texte, le surlignage et les cellules. */
export const COULEURS: { nom: string; valeur: string }[] = [
  { nom: 'Noir', valeur: '#0e0e0e' },
  { nom: 'Bleu AXA', valeur: '#00008f' },
  { nom: 'Bleu foncé', valeur: '#0c0e45' },
  { nom: 'Bleu clair', valeur: '#6574f8' },
  { nom: 'Bleu pâle', valeur: '#e2efff' },
  { nom: 'Rouge AXA', valeur: '#ff1721' },
  { nom: 'Rouge foncé', valeur: '#750707' },
  { nom: 'Rouge pâle', valeur: '#ffeaea' },
  { nom: 'Gris', valeur: '#999999' },
  { nom: 'Gris clair', valeur: '#e6e6e6' },
  { nom: 'Blanc', valeur: '#ffffff' },
  { nom: 'Jaune', valeur: '#fff06c' },
  { nom: 'Vert', valeur: '#58c645' },
  { nom: 'Menthe', valeur: '#81eebb' },
  { nom: 'Ciel', valeur: '#74bde8' },
  { nom: 'Corail', valeur: '#ff9c62' },
  { nom: 'Cerise', valeur: '#a30245' },
  { nom: 'Sarcelle', valeur: '#0f717f' },
  { nom: 'Raisin', valeur: '#614fe8' },
  { nom: 'Rose', valeur: '#ffb4ce' },
];

export const CARACTERES_SPECIAUX = [
  '☎',
  '✉',
  '€',
  '§',
  '°',
  '«',
  '»',
  '–',
  '—',
  '…',
  '©',
  '®',
  '™',
  '½',
  '¼',
  '¾',
  '→',
  '•',
  '✓',
  '⚠',
  'n°',
  'N°',
];

/** Largeurs proposées pour une image insérée (pourcentage de la largeur du texte). */
export const LARGEURS_IMAGE = ['25%', '50%', '75%', '100%'];

/** Contraintes des images insérées : PNG / JPEG, 1 Mo maximum (mêmes règles côté serveur). */
export const IMAGE_TYPES = ['image/png', 'image/jpeg'];
export const IMAGE_TAILLE_MAX = 1024 * 1024;

/** Niveaux de zoom de la feuille (pourcentage). */
export const ZOOMS = [75, 100, 125, 150];
