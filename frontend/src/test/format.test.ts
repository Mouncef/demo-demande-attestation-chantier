import { describe, expect, it } from 'vitest';
import { dureeRestante, formatMontant, formatTaille } from '@/lib/format';

describe('formatage', () => {
  it('formate les montants en euros', () => {
    expect(formatMontant('1250000.5').replace(/[\u202f\u00a0]/g, ' ')).toBe('1 250 000,50 €');
    expect(formatMontant(null)).toBe('—');
  });
  it('formate les tailles', () => {
    expect(formatTaille(512)).toBe('512 o');
    expect(formatTaille(2048)).toBe('2.0 Ko');
  });
  it('calcule la durée restante', () => {
    const maintenant = Date.parse('2026-09-15T10:00:00Z');
    expect(dureeRestante('2026-09-15T13:12:00Z', maintenant)).toBe('3 h 12 min');
    expect(dureeRestante('2026-09-15T09:00:00Z', maintenant)).toBeNull();
  });
});
