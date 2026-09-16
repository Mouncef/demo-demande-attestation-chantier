// Rôles de couleurs du reporting – Data palette de la charte AXA (réservée aux infographies), validée avec le
// script du skill dataviz sur surface blanche (ordre adjacent : Leaf / Grape / Cherry, toutes vérifications OK ;
// Leaf sous 3:1 de contraste → libellés directs et vue tableau présents). La couleur suit l'entité ; le texte
// reste en tokens de texte, jamais dans la couleur de la série.

/** Séries de décision, ordre fixe pour les empilements (paires adjacentes validées CVD). */
export const SERIES_DECISION = [
  { cle: 'acceptees', libelle: 'Acceptées', couleur: '#58C645' }, // Leaf
  { cle: 'en_instruction', libelle: 'En instruction', couleur: '#614FE8' }, // Grape
  { cle: 'refusees', libelle: 'Refusées', couleur: '#A30245' }, // Cherry
] as const;

/** Brouillons : neutre (Light grey), pas encore engagés dans le circuit. */
export const COULEUR_BROUILLON = '#E6E6E6';

/** Série unique (barres nominales) : Grape. */
export const COULEUR_SERIE = '#614FE8';

/** Rampe ordinale bleue (une seule teinte, clair → foncé, validée `--ordinal`) : Blue Tint 2 → AXA Blue → Blue Tint 3. */
export const RAMPE_ORDINALE = ['#6574F8', '#00008F', '#0C0E45'] as const;
export const COULEUR_NON_EVALUE = '#E6E6E6';

/** Chrome des graphiques : grille et axes en Light grey, texte en Black / Blue Tint 3. */
export const CHROME = {
  grille: '#E6E6E6',
  axe: '#999999',
  texte: '#0E0E0E',
  texteSecondaire: '#0C0E45',
  surface: '#FFFFFF',
} as const;

/** Format d'un mois « 2026-09 » → « sept. 2026 ». */
export function formatMois(mois: string): string {
  const [annee, m] = mois.split('-').map(Number);
  return new Intl.DateTimeFormat('fr-FR', { month: 'short', year: 'numeric' }).format(
    new Date(annee, m - 1, 1),
  );
}
