// Schéma de validation du FDR côté client (mode brouillon : formats + règles croisées).
// L'obligation des champs pour l'envoi est vérifiée par le backend (`erreurs_fdr`).
import { z } from 'zod';
import { parseMontant } from './reglesPieces';

/** Contrôle de Luhn (SIRET). */
export function luhnValide(chiffres: string): boolean {
  let total = 0;
  [...chiffres].reverse().forEach((c, i) => {
    let n = Number(c);
    if (i % 2 === 1) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    total += n;
  });
  return total % 10 === 0;
}

const texte = (max: number) => z.string().max(max, `${max} caractères maximum`).nullable();
const montant = z
  .string()
  .nullable()
  .refine(
    (v) => v === null || v === '' || /^\d{1,10}([.,]\d{1,2})?$/.test(v.replace(/[\s\u202f\u00a0]/g, '')),
    'Montant invalide (2 décimales maximum)',
  )
  .refine((v) => v === null || v === '' || (parseMontant(v) ?? 0) > 0, 'Le montant doit être positif');
const dateIso = z
  .string()
  .nullable()
  .refine((v) => !v || /^\d{4}-\d{2}-\d{2}$/.test(v), 'Date invalide');
const booleen = z.boolean().nullable();

export const schemaFdr = z
  .object({
    assure_nom: texte(200),
    assure_adresse: texte(200),
    assure_code_postal: z
      .string()
      .nullable()
      .transform((v) => (v ? v.replace(/\s/g, '') : v))
      .refine((v) => !v || /^\d{5}$/.test(v), 'Le code postal doit comporter 5 chiffres.'),
    assure_ville: texte(100),
    assure_siret: z
      .string()
      .nullable()
      .transform((v) => (v ? v.replace(/\s/g, '') : v))
      .refine((v) => !v || /^\d{14}$/.test(v), 'Le SIRET doit comporter 14 chiffres.')
      .refine((v) => !v || luhnValide(v), 'Le SIRET est invalide (clé de contrôle).'),
    numero_contrat: z
      .string()
      .nullable()
      .transform((v) => (v ? v.toUpperCase().replace(/[\s-]/g, '') : v))
      .refine((v) => !v || /^[A-Z0-9]{6,20}$/.test(v), '6 à 20 caractères alphanumériques'),
    reference_client: texte(30),
    chantier_nom: texte(200),
    chantier_ville: texte(100),
    type_chantier: z.enum(['CONSTRUCTION_NEUVE', 'RENOVATION']).nullable(),
    modification_structure: booleen,
    usage: z.enum(['HABITATION', 'BUREAU', 'COMMERCE', 'AUTRE']).nullable(),
    usage_autre_precision: texte(200),
    chantier_atypique: booleen,
    date_debut: dateIso,
    date_fin: dateIso,
    cout_total: montant,
    description_travaux: texte(4000),
    montant_prestation: montant,
    type_intervention: z.enum(['ENTREPRISE_PRINCIPALE', 'SOUS_TRAITANT']).nullable(),
    entreprise_principale_nom: texte(200),
    activite_couverte: booleen,
    activite_non_couverte_precision: texte(2000),
    travaux_standards: booleen,
  })
  .superRefine((v, ctx) => {
    if (v.date_debut && v.date_fin && v.date_fin < v.date_debut) {
      ctx.addIssue({
        code: 'custom',
        path: ['date_fin'],
        message: 'La date de fin doit être postérieure ou égale à la date de début.',
      });
    }
    const cout = parseMontant(v.cout_total);
    const prestation = parseMontant(v.montant_prestation);
    if (cout !== null && prestation !== null && prestation > cout) {
      ctx.addIssue({
        code: 'custom',
        path: ['montant_prestation'],
        message: 'Le montant de la prestation ne peut pas dépasser le coût total.',
      });
    }
    if (v.usage === 'AUTRE' && v.usage_autre_precision && v.usage_autre_precision.length < 3) {
      ctx.addIssue({ code: 'custom', path: ['usage_autre_precision'], message: '3 caractères minimum.' });
    }
    if (
      v.activite_couverte === false &&
      v.activite_non_couverte_precision &&
      v.activite_non_couverte_precision.length < 10
    ) {
      ctx.addIssue({
        code: 'custom',
        path: ['activite_non_couverte_precision'],
        message: '10 caractères minimum.',
      });
    }
  });

/** Champs obligatoires pour passer à l'étape suivante / envoyer (miroir de CHAMPS_OBLIGATOIRES_ENVOI backend). */
export const CHAMPS_OBLIGATOIRES: (keyof z.input<typeof schemaFdr>)[] = [
  'assure_nom',
  'assure_adresse',
  'assure_code_postal',
  'assure_ville',
  'assure_siret',
  'numero_contrat',
  'chantier_nom',
  'chantier_ville',
  'type_chantier',
  'usage',
  'chantier_atypique',
  'date_debut',
  'date_fin',
  'cout_total',
  'description_travaux',
  'montant_prestation',
  'type_intervention',
  'activite_couverte',
  'travaux_standards',
];

const OBLIGATOIRE = 'Ce champ est obligatoire.';
const JOUR_MS = 86_400_000;

/**
 * Schéma complet (mode « envoi ») : formats + règles croisées du brouillon, plus les obligations.
 * Utilisé au clic sur « Suivant » dans le parcours : on ne passe à l'étape suivante qu'avec un FDR complet.
 */
export const schemaFdrEnvoi = schemaFdr.superRefine((v, ctx) => {
  const manquant = (champ: keyof typeof v) =>
    ctx.addIssue({ code: 'custom', path: [champ], message: OBLIGATOIRE });
  for (const champ of CHAMPS_OBLIGATOIRES) {
    const valeur = v[champ];
    if (valeur === null || valeur === undefined || valeur === '') manquant(champ);
  }
  if (v.type_chantier === 'RENOVATION' && v.modification_structure === null) {
    ctx.addIssue({
      code: 'custom',
      path: ['modification_structure'],
      message: 'Indiquez si la structure est modifiée.',
    });
  }
  if (v.usage === 'AUTRE' && !v.usage_autre_precision) {
    ctx.addIssue({
      code: 'custom',
      path: ['usage_autre_precision'],
      message: "Précisez l'usage de l'ouvrage.",
    });
  }
  if (v.activite_couverte === false && !v.activite_non_couverte_precision) {
    ctx.addIssue({
      code: 'custom',
      path: ['activite_non_couverte_precision'],
      message: "Décrivez l'activité non couverte par le contrat.",
    });
  }
  if (v.description_travaux && v.description_travaux.length < 20) {
    ctx.addIssue({
      code: 'custom',
      path: ['description_travaux'],
      message: 'Décrivez les travaux plus précisément (20 caractères minimum).',
    });
  }
  if (v.date_debut) {
    const debut = new Date(v.date_debut).getTime();
    const aujourdhui = Date.now();
    if (debut < aujourdhui - 365 * JOUR_MS) {
      ctx.addIssue({
        code: 'custom',
        path: ['date_debut'],
        message: "La date de début ne peut pas être antérieure de plus d'un an.",
      });
    } else if (debut > aujourdhui + 3 * 365 * JOUR_MS) {
      ctx.addIssue({
        code: 'custom',
        path: ['date_debut'],
        message: 'La date de début ne peut pas être à plus de trois ans.',
      });
    }
  }
});

export type FdrFormValues = z.input<typeof schemaFdr>;
export type FdrFormOutput = z.output<typeof schemaFdr>;

/** Normalise les valeurs avant envoi à l'API : montants au format « 1234.56 », chaînes vides → null. */
export function versPayload(v: FdrFormOutput): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  for (const [cle, valeur] of Object.entries(v)) {
    if (valeur === '' || valeur === undefined) payload[cle] = null;
    else if ((cle === 'cout_total' || cle === 'montant_prestation') && typeof valeur === 'string') {
      const n = parseMontant(valeur);
      payload[cle] = n === null ? null : n.toFixed(2);
    } else payload[cle] = valeur;
  }
  return payload;
}

/** Valeurs de formulaire à partir du FDR renvoyé par l'API. */
export function depuisFdr(fdr: Record<string, unknown>): FdrFormValues {
  const champs = Object.keys(schemaFdr.shape) as (keyof FdrFormValues)[];
  const valeurs = {} as Record<string, unknown>;
  for (const c of champs) valeurs[c] = fdr[c] ?? null;
  // Montants présentés au format français (« 1 250 000,00 ») ; le schéma accepte ce format en retour.
  for (const c of ['cout_total', 'montant_prestation'] as const) {
    const n = parseMontant(valeurs[c] as string | null);
    valeurs[c] =
      n === null
        ? null
        : new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
  }
  return valeurs as FdrFormValues;
}
