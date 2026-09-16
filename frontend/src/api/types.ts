// Types TypeScript miroir des serializers du backend (source de vérité : /api/schema/).

export type Role = 'DISTRIBUTEUR' | 'SIEGE';
export type Statut = 'BROUILLON' | 'EN_COURS' | 'A_COMPLETER' | 'TRAITE';
export type Decision = 'ACCEPTEE' | 'REFUSEE' | null;
export type NiveauRisque = 'FAIBLE' | 'MODERE' | 'ELEVE';
export type TypeChantier = 'CONSTRUCTION_NEUVE' | 'RENOVATION';
export type Usage = 'HABITATION' | 'BUREAU' | 'COMMERCE' | 'AUTRE';
export type TypeIntervention = 'ENTREPRISE_PRINCIPALE' | 'SOUS_TRAITANT';
export type KindAttestation = 'PROJET' | 'DEFINITIVE';
export type EtatAttestation =
  'AUCUNE' | 'PROJET_EN_COURS' | 'PROJET_SOUMIS' | 'PROJET_A_CORRIGER' | 'DEFINITIVE';
export type StatutAttestation = 'EN_EDITION' | 'SOUMISE' | 'A_CORRIGER' | 'VALIDEE';

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

export type ActionPossible =
  | 'modifier_fdr'
  | 'gerer_pieces'
  | 'envoyer'
  | 'supprimer'
  | 'relancer'
  | 'editer_projet_attestation'
  | 'accepter'
  | 'refuser'
  | 'demander_complements'
  | 'commenter'
  | 'editer_attestation_definitive'
  | 'telecharger_attestation_definitive'
  | 'traiter_projet_attestation';

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
  prochaine_relance_possible: string | null;
  etat_attestation: EtatAttestation;
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
  nb_relances: number;
  derniere_relance_le: string | null;
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

export interface Relance {
  id: number;
  message: string;
  destinataires: string[];
  email_ok: boolean;
  envoyee_par: UtilisateurLeger;
  created_at: string;
}

export interface Soumission {
  id: number;
  numero: number;
  fdr_snapshot: FDR;
  pieces_snapshot: unknown[];
  scoring_snapshot: Scoring;
  commentaire_distributeur: string;
  created_at: string;
}

export interface Incoherence {
  code: string;
  severite: 'MAJEURE' | 'MOYENNE' | 'MINEURE';
  champ: string | null;
  message: string;
  attendu: string | null;
  trouve: string | null;
  extrait: string | null;
  offset: number | null;
  longueur: number | null;
}

export interface ResultatAnalyse {
  statut: 'COHERENT' | 'INCOHERENT';
  score: number;
  contenu_hash: string;
  resume: string;
  incoherences: Incoherence[];
  controles_ok: string[];
}

export interface AnalyseIA {
  id: string;
  statut: 'COHERENT' | 'INCOHERENT';
  score: number;
  contenu_hash: string;
  resultat: ResultatAnalyse;
  created_by: string;
  created_at: string;
}

export interface Attestation {
  id: string;
  kind: KindAttestation;
  statut: StatutAttestation;
  contenu_html: string;
  contenu_json: unknown;
  variables_snapshot: Record<string, string | boolean>;
  numero: string;
  pdf_disponible: boolean;
  created_by: string;
  validated_at: string | null;
  validated_by: string | null;
  justification_forcage: string;
  /** Projet : date de soumission au siège. */
  soumise_le: string | null;
  /** Projet : commentaire du siège lorsqu'il est renvoyé pour correction. */
  commentaire_siege: string;
  derniere_analyse: AnalyseIA | null;
  /** La dernière analyse porte-t-elle sur le contenu enregistré ? */
  analyse_a_jour: boolean;
  created_at: string;
  updated_at: string;
}

export interface Gabarit {
  contenu_html: string;
  contenu_json: unknown;
  variables: Record<string, string | boolean>;
  variables_disponibles: Record<string, string>;
  source: 'GABARIT' | 'PROJET';
  /** Date de soumission du projet repris comme base (définitive). */
  projet_soumis_le: string | null;
  /** Identité de l'assureur (en-tête du document). */
  assureur: { nom: string; forme: string; rcs: string; adresse: string; mention: string };
  /** Cadre non modifiable du format officiel AXA (page 1 et en-tête courant). */
  entete: EnteteAttestation;
}

export interface EnteteAttestation {
  accroche: string;
  intermediaire: { nom: string; adresse: string; telephone: string; email: string };
  produit: string;
  numero_contrat: string;
  reference_client: string;
  destinataire: { nom: string; adresse: string; cp_ville: string };
  date_courrier: string;
  mentions_legales: string;
}

export interface Notification {
  id: string;
  type: string;
  titre: string;
  message: string;
  payload: {
    demande_id?: string;
    reference?: string;
    statut?: Statut;
    decision?: Decision;
    onglet?: string | null;
  };
  lu: boolean;
  lu_le: string | null;
  created_at: string;
  demande: string | null;
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
  relance_cooldown_hours: number;
  upload: { max_bytes: number; extensions: string[] };
}

export type PeriodeReporting = '30' | '90' | '365' | 'tout';

export interface LigneMensuelle {
  mois: string;
  total: number;
  acceptees: number;
  refusees: number;
  en_instruction: number;
  brouillons: number;
}

export interface LigneDistributeur {
  nom: string;
  total: number;
  acceptees: number;
  refusees: number;
  en_instruction: number;
  brouillons: number;
}

export interface Reporting {
  periode: PeriodeReporting;
  total: number;
  par_statut: Record<Statut, number>;
  acceptees: number;
  refusees: number;
  en_instruction: number;
  taux_acceptation: number | null;
  delai_moyen_traitement_jours: number | null;
  delai_moyen_decision_jours: number | null;
  delai_moyen_attestation_jours: number | null;
  par_mois: LigneMensuelle[];
  par_niveau_risque: Record<NiveauRisque | 'NON_EVALUE', number>;
  circuit_attestation: { acceptees: number; projets_soumis: number; attestations_etablies: number };
  /** Siège : en cours d'instruction + projets soumis ; distributeur : compléments demandés + projets à corriger. */
  a_traiter: number;
  /** Siège uniquement : distributeurs les plus actifs (le reste plié dans « Autres »). */
  par_distributeur?: LigneDistributeur[];
  /** Distributeur uniquement : assurés les plus fréquents (même structure). */
  par_assure?: LigneDistributeur[];
}

/** Format d'erreur normalisé renvoyé par le backend. */
export interface ErreurApi {
  code: string;
  detail: string;
  errors?: Record<string, string[] | string>;
  [extra: string]: unknown;
}
