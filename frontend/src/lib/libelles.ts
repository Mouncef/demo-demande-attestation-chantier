// Libellés métier centralisés (statuts, décisions, niveaux de risque, erreurs API).
import type { Decision, NiveauRisque, Statut } from '@/api/types';

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

export const LIBELLES_ERREURS_API: Record<string, string> = {
  INTERDIT: "Vous n'avez pas les droits nécessaires pour cette action.",
  INTROUVABLE: 'Ressource introuvable ou inaccessible.',
  NON_AUTHENTIFIE: 'Votre session a expiré, veuillez vous reconnecter.',
  VALIDATION: 'Certaines données sont invalides.',
  RESEAU: 'Le serveur est injoignable.',
};
