// Libellés métier centralisés (statuts, décisions, niveaux, énumérations du FDR, erreurs API).
import type { Decision, NiveauRisque, Statut, TypeChantier, TypeIntervention, Usage } from '@/api/types';

export const LIBELLES_STATUT: Record<Statut, string> = {
  BROUILLON: 'Brouillon',
  EN_COURS: 'En cours',
  A_COMPLETER: 'Compléments demandés',
  TRAITE: 'Traitée',
};

export const LIBELLES_DECISION: Record<NonNullable<Decision>, string> = {
  ACCEPTEE: 'Acceptée',
  REFUSEE: 'Refusée',
};

export const LIBELLES_NIVEAU: Record<NiveauRisque, string> = {
  FAIBLE: 'Faible',
  MODERE: 'Modéré',
  ELEVE: 'Élevé',
};

export const LIBELLES_TYPE_CHANTIER: Record<TypeChantier, string> = {
  CONSTRUCTION_NEUVE: 'Construction neuve',
  RENOVATION: 'Rénovation',
};

export const LIBELLES_USAGE: Record<Usage, string> = {
  HABITATION: 'Habitation',
  BUREAU: 'Bureau',
  COMMERCE: 'Commerce',
  AUTRE: 'Autre',
};

export const LIBELLES_INTERVENTION: Record<TypeIntervention, string> = {
  ENTREPRISE_PRINCIPALE: 'Entreprise principale',
  SOUS_TRAITANT: 'Sous-traitant',
};

export const LIBELLES_ERREURS_API: Record<string, string> = {
  TRANSITION_INVALIDE: "Cette action n'est pas possible dans l'état actuel de la demande.",
  DOSSIER_INCOMPLET: 'Le dossier est incomplet : des pièces requises manquent.',
  CONFLIT_VERSION: 'La demande a été modifiée entre-temps. Les données ont été rechargées.',
  RELANCE_TROP_TOT: 'Une relance a déjà été envoyée : le délai de 24 h n’est pas écoulé.',
  INTERDIT: "Vous n'avez pas les droits nécessaires pour cette action.",
  INTROUVABLE: 'Ressource introuvable ou inaccessible.',
  NON_AUTHENTIFIE: 'Votre session a expiré, veuillez vous reconnecter.',
  VALIDATION: 'Certaines données sont invalides.',
  TYPE_FICHIER_NON_AUTORISE: "Ce type de fichier n'est pas autorisé.",
  FICHIER_TROP_VOLUMINEUX: 'Le fichier dépasse la taille maximale autorisée.',
  PIECE_DUPLIQUEE: 'Ce fichier a déjà été déposé sur cette demande.',
  QUOTA_PIECES: 'Nombre ou volume maximal de pièces atteint.',
  RESEAU: 'Le serveur est injoignable.',
};
