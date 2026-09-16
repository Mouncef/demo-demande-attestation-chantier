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
  CONFLIT_VERSION: 'La demande a été modifiée entre-temps. Les données ont été rechargées.',
  INTERDIT: "Vous n'avez pas les droits nécessaires pour cette action.",
  INTROUVABLE: 'Ressource introuvable ou inaccessible.',
  NON_AUTHENTIFIE: 'Votre session a expiré, veuillez vous reconnecter.',
  VALIDATION: 'Certaines données sont invalides.',
  RESEAU: 'Le serveur est injoignable.',
};
