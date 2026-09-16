import type { ReactNode } from 'react';
import { Button } from './Button';
import { TAILLES_PAGE } from '../pagination';

export function Spinner({ label = 'Chargement…' }: { label?: string }) {
  return (
    <div className="flex" role="status" style={{ padding: '1rem 0' }}>
      <span className="spinner" aria-hidden /> <span className="muted">{label}</span>
    </div>
  );
}

export function EmptyState({ titre, children }: { titre: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <h3 style={{ color: 'var(--axa-gray-700)' }}>{titre}</h3>
      {children}
    </div>
  );
}

export function Pagination({
  page,
  total,
  taille,
  onChange,
  onTailleChange,
  tailles = TAILLES_PAGE,
}: {
  page: number;
  total: number;
  taille: number;
  onChange: (p: number) => void;
  /** Si fourni, affiche le sélecteur « Lignes par page » et la pagination même sur une seule page. */
  onTailleChange?: (taille: number) => void;
  tailles?: readonly number[];
}) {
  const pages = Math.max(1, Math.ceil(total / taille));
  if (pages <= 1 && !onTailleChange) return null;
  const debut = total === 0 ? 0 : (page - 1) * taille + 1;
  const fin = Math.min(page * taille, total);
  return (
    <nav className="pagination" aria-label="Pagination">
      {onTailleChange && (
        <label className="pagination__taille small">
          Lignes par page
          <select
            className="select select--sm"
            value={taille}
            onChange={(e) => onTailleChange(Number(e.target.value))}
            aria-label="Lignes par page"
          >
            {tailles.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
      )}
      <span className="muted small" aria-live="polite">
        {total === 0 ? 'Aucun résultat' : `${debut}–${fin} sur ${total}`} · Page {page} / {pages}
      </span>
      <Button variante="secondary" taille="sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        ← Précédent
      </Button>
      <Button variante="secondary" taille="sm" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Suivant →
      </Button>
    </nav>
  );
}

export function Kpi({ valeur, label, couleur }: { valeur: ReactNode; label: string; couleur?: string }) {
  return (
    <div className="kpi" style={couleur ? { borderLeftColor: couleur } : undefined}>
      <div className="kpi__value">{valeur}</div>
      <div className="kpi__label">{label}</div>
    </div>
  );
}
