import { describe, expect, it } from 'vitest';
import { calculerExigencesClient, parseMontant } from '@/features/fdr/reglesPieces';

describe('règles de pièces côté client', () => {
  it('ne requiert rien par défaut', () => {
    expect(calculerExigencesClient({})).toEqual([]);
  });

  it('déclenche les pièces structure et gros chantier (seuil strict)', () => {
    const codes = calculerExigencesClient({ modification_structure: true, cout_total: '10000000.01' }).map(
      (e) => e.code,
    );
    expect(codes).toEqual([
      'ETUDE_STRUCTURE',
      'AUTORISATION_URBANISME',
      'MARCHE_SIGNE',
      'ATTESTATION_DO',
      'PLANNING_PREVISIONNEL',
    ]);
    expect(calculerExigencesClient({ cout_total: '10000000' })).toEqual([]);
  });

  it('marque la sous-traitance comme recommandée', () => {
    const [e] = calculerExigencesClient({ type_intervention: 'SOUS_TRAITANT' });
    expect(e).toMatchObject({ code: 'CONTRAT_SOUS_TRAITANCE', niveau: 'RECOMMANDE' });
  });

  it('parse les montants français', () => {
    expect(parseMontant('1 250 000,50')).toBe(1250000.5);
    expect(parseMontant('abc')).toBeNull();
    expect(parseMontant('')).toBeNull();
  });
});
