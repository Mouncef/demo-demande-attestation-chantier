import type { ReactNode } from 'react';
import type { Decision, NiveauRisque, Statut } from '@/api/types';
import { LIBELLES_DECISION, LIBELLES_NIVEAU, LIBELLES_STATUT } from '@/lib/libelles';

type Couleur = 'gray' | 'blue' | 'green' | 'orange' | 'red' | 'dark' | 'strong';

export function Badge({ couleur = 'gray', children }: { couleur?: Couleur; children: ReactNode }) {
  return <span className={`badge badge--${couleur}`}>{children}</span>;
}

const COULEUR_STATUT: Record<Statut, Couleur> = {
  BROUILLON: 'gray',
  EN_COURS: 'blue',
  A_COMPLETER: 'orange',
  TRAITE: 'dark',
};

export function BadgeStatut({ statut }: { statut: Statut }) {
  return <Badge couleur={COULEUR_STATUT[statut]}>{LIBELLES_STATUT[statut]}</Badge>;
}

export function BadgeDecision({ decision }: { decision: Decision }) {
  if (!decision) return null;
  return <Badge couleur={decision === 'ACCEPTEE' ? 'green' : 'red'}>{LIBELLES_DECISION[decision]}</Badge>;
}

// Niveau élevé : Red Tint 3 avec texte blanc (RT3→W : AAA).
const COULEUR_NIVEAU: Record<NiveauRisque, Couleur> = { FAIBLE: 'green', MODERE: 'orange', ELEVE: 'strong' };

export function BadgeNiveau({ niveau }: { niveau: NiveauRisque | null | undefined }) {
  if (!niveau) return <span className="muted">—</span>;
  return <Badge couleur={COULEUR_NIVEAU[niveau]}>Risque {LIBELLES_NIVEAU[niveau]}</Badge>;
}
