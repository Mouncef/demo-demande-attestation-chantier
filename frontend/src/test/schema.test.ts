import { describe, expect, it } from 'vitest';
import { depuisFdr, schemaFdr, schemaFdrEnvoi, versPayload } from '@/features/fdr/schema';

const base = depuisFdr({});

describe('schéma FDR (mode brouillon)', () => {
  it('accepte un brouillon vide', () => {
    expect(schemaFdr.safeParse(base).success).toBe(true);
  });

  it('normalise le numéro de contrat et refuse un format invalide', () => {
    const ok = schemaFdr.safeParse({ ...base, numero_contrat: 'rcd 2026-ly0142' });
    expect(ok.success && ok.data.numero_contrat).toBe('RCD2026LY0142');
    expect(schemaFdr.safeParse({ ...base, numero_contrat: 'ab' }).success).toBe(false);
  });

  it('valide le SIRET (14 chiffres, clé de Luhn) et le code postal', () => {
    expect(schemaFdr.safeParse({ ...base, assure_siret: '833 207 194 00014' }).success).toBe(true);
    expect(schemaFdr.safeParse({ ...base, assure_siret: '83320719400015' }).success).toBe(false);
    expect(schemaFdr.safeParse({ ...base, assure_code_postal: '6900' }).success).toBe(false);
  });

  it('refuse une date de fin antérieure au début', () => {
    const res = schemaFdr.safeParse({ ...base, date_debut: '2026-10-01', date_fin: '2026-09-01' });
    expect(res.success).toBe(false);
    expect(!res.success && res.error.issues[0].path).toEqual(['date_fin']);
  });

  it('refuse une prestation supérieure au coût total', () => {
    const res = schemaFdr.safeParse({ ...base, cout_total: '1 000 000,00', montant_prestation: '1200000' });
    expect(res.success).toBe(false);
  });

  it('convertit les montants au format API', () => {
    const res = schemaFdr.safeParse({ ...base, cout_total: '1 250 000,5', montant_prestation: '' });
    expect(res.success).toBe(true);
    if (res.success) {
      const payload = versPayload(res.data);
      expect(payload.cout_total).toBe('1250000.50');
      expect(payload.montant_prestation).toBeNull();
    }
  });
});

describe('schéma FDR (mode envoi, clic sur « Suivant »)', () => {
  const complet = {
    ...base,
    assure_nom: 'SAS TEST',
    assure_adresse: '1 rue de Test',
    assure_code_postal: '69001',
    assure_ville: 'Lyon',
    assure_siret: '83320719400014',
    numero_contrat: 'RCD2026LY0142',
    chantier_nom: 'Chantier',
    chantier_ville: 'Lyon',
    type_chantier: 'CONSTRUCTION_NEUVE' as const,
    usage: 'BUREAU' as const,
    chantier_atypique: false,
    date_debut: new Date(Date.now() + 30 * 86_400_000).toISOString().slice(0, 10),
    date_fin: new Date(Date.now() + 200 * 86_400_000).toISOString().slice(0, 10),
    cout_total: '1 000 000,00',
    description_travaux: 'Gros œuvre et maçonnerie du bâtiment principal.',
    montant_prestation: '250000',
    type_intervention: 'ENTREPRISE_PRINCIPALE' as const,
    activite_couverte: true,
    travaux_standards: true,
  };

  it('refuse un brouillon vide et liste chaque champ obligatoire', () => {
    const res = schemaFdrEnvoi.safeParse(base);
    expect(res.success).toBe(false);
    if (!res.success) expect(res.error.issues.map((i) => i.path[0])).toContain('assure_nom');
  });

  it('accepte un FDR complet', () => {
    expect(schemaFdrEnvoi.safeParse(complet).success).toBe(true);
  });

  it('exige les champs conditionnels', () => {
    const res = schemaFdrEnvoi.safeParse({
      ...complet,
      type_chantier: 'RENOVATION',
      usage: 'AUTRE',
      activite_couverte: false,
    });
    expect(res.success).toBe(false);
    if (!res.success) {
      const champs = res.error.issues.map((i) => i.path[0]);
      expect(champs).toEqual(
        expect.arrayContaining([
          'modification_structure',
          'usage_autre_precision',
          'activite_non_couverte_precision',
        ]),
      );
    }
  });

  it('refuse une description trop courte et une date trop ancienne', () => {
    const res = schemaFdrEnvoi.safeParse({
      ...complet,
      description_travaux: 'court',
      date_debut: '2020-01-01',
      date_fin: '2020-02-01',
    });
    expect(res.success).toBe(false);
    if (!res.success)
      expect(res.error.issues.map((i) => i.path[0])).toEqual(
        expect.arrayContaining(['description_travaux', 'date_debut']),
      );
  });
});
