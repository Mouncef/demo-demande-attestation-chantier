import type { ReactNode } from 'react';

interface Props {
  titre?: ReactNode;
  actions?: ReactNode;
  variante?: 'default' | 'plain' | 'danger' | 'success';
  children: ReactNode;
  className?: string;
}

export function Card({ titre, actions, variante = 'default', children, className = '' }: Props) {
  return (
    <section className={`card ${variante !== 'default' ? `card--${variante}` : ''} ${className}`}>
      {(titre || actions) && (
        <div className="card__title">
          {typeof titre === 'string' ? <h2>{titre}</h2> : titre}
          {actions && <div className="actions">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}
