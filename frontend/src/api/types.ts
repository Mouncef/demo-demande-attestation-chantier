// Types TypeScript miroir des serializers du backend (source de vérité : /api/schema/).

export type Role = 'DISTRIBUTEUR' | 'SIEGE';
export type Statut = 'BROUILLON' | 'EN_COURS' | 'A_COMPLETER' | 'TRAITE';
export type Decision = 'ACCEPTEE' | 'REFUSEE' | null;
export type NiveauRisque = 'FAIBLE' | 'MODERE' | 'ELEVE';
export type TypeChantier = 'CONSTRUCTION_NEUVE' | 'RENOVATION';
export type Usage = 'HABITATION' | 'BUREAU' | 'COMMERCE' | 'AUTRE';
export type TypeIntervention = 'ENTREPRISE_PRINCIPALE' | 'SOUS_TRAITANT';

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

export interface UtilisateurLeger {
  id: number;
  nom_affichage: string;
  email: string;
  organisation: string;
}

/** Formulaire de Déclaration du Risque – tous les champs sont nullables (brouillon). */
export interface FDR {
  assure_nom: string | null;
  assure_adresse: string | null;
  assure_code_postal: string | null;
  assure_ville: string | null;
  assure_siret: string | null;
  numero_contrat: string | null;
  reference_client: string | null;
  chantier_nom: string | null;
  chantier_ville: string | null;
  type_chantier: TypeChantier | null;
  modification_structure: boolean | null;
  usage: Usage | null;
  usage_autre_precision: string | null;
  chantier_atypique: boolean | null;
  date_debut: string | null;
  date_fin: string | null;
  cout_total: string | null;
  description_travaux: string | null;
  montant_prestation: string | null;
  type_intervention: TypeIntervention | null;
  entreprise_principale_nom: string | null;
  activite_couverte: boolean | null;
  activite_non_couverte_precision: string | null;
  travaux_standards: boolean | null;
}

export type ActionPossible = 'modifier_fdr' | 'gerer_pieces' | 'supprimer';

export interface DemandeListe {
  id: string;
  reference: string;
  statut: Statut;
  decision: Decision;
  distributeur: UtilisateurLeger;
  assure_nom: string | null;
  chantier_nom: string | null;
  chantier_ville: string | null;
  cout_total: string | null;
  niveau_risque: NiveauRisque | null;
  submitted_at: string | null;
  decided_at: string | null;
  nb_soumissions: number;
  created_at: string;
  updated_at: string;
  actions_possibles: ActionPossible[];
}

export interface Indicateur {
  code: string;
  libelle: string;
  points: number;
  detail: string;
}

export interface Scoring {
  points: number;
  score: number;
  niveau: NiveauRisque;
  indicateurs: Indicateur[];
  planchers: string[];
  synthese: string;
}

export interface DemandeDetail extends DemandeListe {
  fdr: FDR;
  version: number;
  commentaire_distributeur: string;
  commentaire_siege: string;
  motif_refus: string;
  message_complements: string;
  first_submitted_at: string | null;
  decided_by: UtilisateurLeger | null;
  scoring_snapshot: Scoring | null;
}

export interface Pagination<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface PieceResume {
  id: string;
  nom_fichier: string;
  nom_original: string;
  type_piece: string;
  taille: number;
  created_at: string | null;
}

export interface EtatExigence {
  code: string;
  libelle: string;
  niveau: 'REQUIS' | 'RECOMMANDE';
  raison: string;
  satisfait: boolean;
  pieces: PieceResume[];
}

export interface Completude {
  complet: boolean;
  exigences: EtatExigence[];
  pieces_hors_exigence: (PieceResume & { libelle: string; info: string })[];
  manquants: string[];
  fdr_valide: boolean;
  erreurs_fdr: Record<string, string>;
  pret_pour_envoi: boolean;
}

export interface PieceJointe {
  id: string;
  type_piece: string;
  libelle_type: string;
  /** Nom de la pièce : libellé du type (+ numéro si doublon) avec extension. */
  nom_fichier: string;
  /** Nom du fichier tel que déposé (information). */
  nom_original: string;
  mime: string;
  taille: number;
  sha256: string;
  deposee_par: string;
  created_at: string;
}

export interface Historique {
  id: number;
  action: string;
  action_libelle: string;
  de_statut: Statut | null;
  vers_statut: Statut | null;
  decision: Decision;
  acteur: UtilisateurLeger;
  commentaire: string;
  created_at: string;
}

export interface Choix {
  code: string;
  libelle: string;
}

export interface Referentiels {
  statuts: Choix[];
  decisions: Choix[];
  types_chantier: Choix[];
  usages: Choix[];
  types_intervention: Choix[];
  types_pieces: (Choix & { description: string })[];
  seuil_gros_chantier: string;
  upload: { max_bytes: number; extensions: string[] };
}

/** Format d'erreur normalisé renvoyé par le backend. */
export interface ErreurApi {
  code: string;
  detail: string;
  errors?: Record<string, string[] | string>;
  [extra: string]: unknown;
}
