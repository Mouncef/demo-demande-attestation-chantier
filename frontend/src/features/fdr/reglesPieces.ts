// Miroir client des règles de pièces requises (backend : apps/demandes/services/exigences.py).
// Sert uniquement à l'affichage en direct dans le formulaire ; le backend reste la référence.
import type { FDR } from '@/api/types';

export interface ExigenceClient {
  code: string;
  niveau: 'REQUIS' | 'RECOMMANDE';
  raison: string;
}

export const SEUIL_GROS_CHANTIER = 10_000_000;

/** Convertit une saisie de montant (« 1 250 000,50 ») en nombre, ou null. */
export function parseMontant(valeur: string | number | null | undefined): number | null {
  if (valeur === null || valeur === undefined || valeur === '') return null;
  if (typeof valeur === 'number') return valeur;
  const nombre = Number(valeur.replace(/[\s\u202f\u00a0]/g, '').replace(',', '.'));
  return Number.isNaN(nombre) ? null : nombre;
}

type Entree = Partial<
  Pick<
    FDR,
    | 'modification_structure'
    | 'chantier_atypique'
    | 'activite_couverte'
    | 'travaux_standards'
    | 'type_intervention'
  >
> & {
  cout_total?: string | number | null;
};

export function calculerExigencesClient(fdr: Entree): ExigenceClient[] {
  const cout = parseMontant(fdr.cout_total);
  const regles: { actif: boolean; codes: string[]; raison: string; niveau?: 'RECOMMANDE' }[] = [
    {
      actif: fdr.modification_structure === true,
      codes: ['ETUDE_STRUCTURE', 'AUTORISATION_URBANISME'],
      raison: 'Rénovation avec modification de la structure',
    },
    {
      actif: fdr.chantier_atypique === true,
      codes: ['DESCRIPTIF_TECHNIQUE', 'PHOTOS_PLANS'],
      raison: 'Chantier atypique',
    },
    {
      actif: cout !== null && cout > SEUIL_GROS_CHANTIER,
      codes: ['MARCHE_SIGNE', 'ATTESTATION_DO', 'PLANNING_PREVISIONNEL'],
      raison: 'Coût total supérieur à 10 M€',
    },
    {
      actif: fdr.activite_couverte === false,
      codes: ['DESCRIPTIF_ACTIVITE', 'JUSTIFICATIF_QUALIFICATION'],
      raison: 'Activité non couverte par le contrat',
    },
    { actif: fdr.travaux_standards === false, codes: ['AVIS_TECHNIQUE'], raison: 'Travaux non standards' },
    {
      actif: fdr.type_intervention === 'SOUS_TRAITANT',
      codes: ['CONTRAT_SOUS_TRAITANCE'],
      raison: 'Intervention en sous-traitance',
      niveau: 'RECOMMANDE',
    },
  ];
  const vus = new Set<string>();
  const resultat: ExigenceClient[] = [];
  for (const r of regles) {
    if (!r.actif) continue;
    for (const code of r.codes) {
      if (vus.has(code)) continue;
      vus.add(code);
      resultat.push({ code, niveau: r.niveau ?? 'REQUIS', raison: r.raison });
    }
  }
  return resultat;
}
