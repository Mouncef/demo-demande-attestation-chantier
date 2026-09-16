import type { ReactNode } from 'react';
import { Button } from './Button';

interface Props {
  onPrecedent?: () => void;
  onSuivant?: () => void;
  libelleSuivant?: string;
  chargement?: boolean;
  /** Actions secondaires placées sur la même ligne, juste avant « Suivant » (ex. enregistrer le brouillon). */
  actions?: ReactNode;
}

/** Barre de navigation d'un parcours en étapes : Précédent à gauche, actions et Suivant à droite. */
export function StepNav({ onPrecedent, onSuivant, libelleSuivant = 'Suivant', chargement, actions }: Props) {
  if (!onPrecedent && !onSuivant && !actions) return null;
  return (
    <div className="step-nav">
      {onPrecedent ? (
        <Button variante="secondary" onClick={onPrecedent} disabled={chargement}>
          ← Précédent
        </Button>
      ) : (
        <span />
      )}
      <div className="step-nav__droite">
        {actions}
        {onSuivant && (
          <Button onClick={onSuivant} chargement={chargement}>
            {libelleSuivant} →
          </Button>
        )}
      </div>
    </div>
  );
}
