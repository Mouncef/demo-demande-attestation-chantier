import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variante = 'primary' | 'secondary' | 'danger' | 'success' | 'ghost';

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: Variante;
  taille?: 'sm' | 'md' | 'lg';
  chargement?: boolean;
  children: ReactNode;
}

/** Bouton AXA : rectangulaire, bleu par défaut ; `chargement` désactive et affiche un spinner. */
export function Button({
  variante = 'primary',
  taille = 'md',
  chargement,
  children,
  className = '',
  disabled,
  ...rest
}: Props) {
  const classes = [
    'btn',
    variante !== 'primary' && `btn--${variante}`,
    taille !== 'md' && `btn--${taille}`,
    className,
  ]
    .filter(Boolean)
    .join(' ');
  return (
    <button type="button" className={classes} disabled={disabled || chargement} {...rest}>
      {chargement && (
        <span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} aria-hidden />
      )}
      {children}
    </button>
  );
}
