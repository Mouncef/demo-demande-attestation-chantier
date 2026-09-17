// Menu déroulant léger (barre d'outils) : bouton déclencheur + panneau, fermeture au clic extérieur ou Escape.
import { useEffect, useId, useRef, useState, type ReactNode } from 'react';

interface Props {
  /** Contenu du bouton déclencheur (texte ou icône). */
  libelle: ReactNode;
  /** Infobulle du bouton. */
  titre?: string;
  disabled?: boolean;
  actif?: boolean;
  className?: string;
  /** Panneau : nœud React ou fonction recevant `fermer`. */
  children: ReactNode | ((fermer: () => void) => ReactNode);
}

export function Menu({ libelle, titre, disabled, actif, className = '', children }: Props) {
  const [ouvert, setOuvert] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const id = useId();

  useEffect(() => {
    if (!ouvert) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOuvert(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOuvert(false);
    };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [ouvert]);

  const fermer = () => setOuvert(false);
  return (
    <div ref={ref} className={`menu ${className}`}>
      <button
        type="button"
        className={`toolbar__btn ${actif ? 'toolbar__btn--actif' : ''}`}
        title={titre}
        aria-label={titre}
        aria-haspopup="true"
        aria-expanded={ouvert}
        aria-controls={id}
        disabled={disabled}
        onClick={() => setOuvert((o) => !o)}
      >
        {libelle}{' '}
        <span className="menu__chevron" aria-hidden>
          ▾
        </span>
      </button>
      {ouvert && (
        <div id={id} className="menu__panneau" role="menu">
          {typeof children === 'function' ? children(fermer) : children}
        </div>
      )}
    </div>
  );
}
