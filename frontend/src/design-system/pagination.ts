/** Tailles de page proposées par le composant Pagination (5 lignes par défaut sur les listes). */
export const TAILLES_PAGE = [5, 10, 20, 50] as const;
export type TaillePage = (typeof TAILLES_PAGE)[number];
