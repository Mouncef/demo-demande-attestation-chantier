// Types TypeScript miroir des serializers du backend (source de vérité : /api/schema/).

export type Role = 'DISTRIBUTEUR' | 'SIEGE';
export type Statut = 'BROUILLON' | 'EN_COURS' | 'A_COMPLETER' | 'TRAITE';
export type Decision = 'ACCEPTEE' | 'REFUSEE' | null;
export type NiveauRisque = 'FAIBLE' | 'MODERE' | 'ELEVE';

export interface Utilisateur {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  nom_affichage: string;
  role: Role;
  organisation: string;
  code_distributeur: string;
  adresse: string;
  telephone: string;
}

export interface LoginReponse {
  access: string;
  refresh: string;
  utilisateur: Utilisateur;
}

/** Format d'erreur normalisé renvoyé par le backend. */
export interface ErreurApi {
  code: string;
  detail: string;
  errors?: Record<string, string[] | string>;
  [extra: string]: unknown;
}
