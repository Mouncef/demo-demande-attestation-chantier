import { describe, expect, it } from 'vitest';
import { cssFeuille } from '@/features/attestation/cssFeuille';

describe('feuille de style du document dans l’éditeur', () => {
  it('retire les blocs @page (y compris imbriqués) et restreint les règles à la feuille', () => {
    const css = `@page { size: A4; @top-left { content: "x"; } }\n.document { font-size: 10pt; }\n@page :first { margin: 0; }\nh1 { color: red; }`;
    const resultat = cssFeuille(css);
    expect(resultat).not.toContain('@page');
    expect(resultat).toContain('.document { font-size: 10pt; }');
    expect(resultat).toContain('h1 { color: red; }');
    expect(resultat.startsWith('.document-attestation {')).toBe(true);
    expect(resultat.trim().endsWith('}')).toBe(true);
  });
});
