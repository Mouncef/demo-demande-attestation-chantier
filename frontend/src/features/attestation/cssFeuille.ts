// Adaptation de la feuille de style du PDF (attestation.css) à la feuille affichée dans l'éditeur.
/** Retire les règles `@page` (réservées au PDF) et restreint la feuille de style à la feuille affichée. */
export function cssFeuille(css: string): string {
  let resultat = '';
  let i = 0;
  while (i < css.length) {
    const debut = css.indexOf('@page', i);
    if (debut === -1) {
      resultat += css.slice(i);
      break;
    }
    resultat += css.slice(i, debut);
    // Saute le bloc @page en équilibrant les accolades (il contient des blocs de marge imbriqués).
    let j = css.indexOf('{', debut);
    let profondeur = 0;
    for (; j < css.length; j++) {
      if (css[j] === '{') profondeur++;
      else if (css[j] === '}' && --profondeur === 0) break;
    }
    i = j + 1;
  }
  return `.document-attestation {\n${resultat}\n}`;
}
