import { useEffect, type ReactNode } from 'react';
import { Button } from './Button';

interface Props {
  ouvert: boolean;
  titre: string;
  onFermer: () => void;
  children: ReactNode;
  pied?: ReactNode;
  large?: boolean;
}

/** Modale accessible (Échap ferme, focus visuel), sans dépendance externe. */
export function Modal({ ouvert, titre, onFermer, children, pied, large }: Props) {
  useEffect(() => {
    if (!ouvert) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onFermer();
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [ouvert, onFermer]);
  if (!ouvert) return null;
  return (
    <div className="modal-backdrop" onClick={onFermer} role="presentation">
      <div
        className={`modal ${large ? 'modal--large' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={titre}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal__header">
          <h3 style={{ margin: 0 }}>{titre}</h3>
          <Button variante="ghost" taille="sm" onClick={onFermer} aria-label="Fermer">
            ✕
          </Button>
        </div>
        <div className="modal__body">{children}</div>
        {pied && <div className="modal__footer">{pied}</div>}
      </div>
    </div>
  );
}
