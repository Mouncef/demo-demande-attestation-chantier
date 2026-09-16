// Info-bulle commune : la valeur en gras, le nom de la série en secondaire, une clé de couleur en trait.
// Les libellés sont rendus en texte (jamais en HTML).
import type { TooltipContentProps } from 'recharts';

interface Props extends Partial<TooltipContentProps<number, string>> {
  /** Formate le libellé de l'axe (ex. mois). */
  formatLibelle?: (valeur: unknown) => string;
  /** Formate une valeur numérique (ex. « 12 » ou « 12 j »). */
  formatValeur?: (valeur: number, cle: string) => string;
}

export function InfoBulle({ active, payload, label, formatLibelle, formatValeur }: Props) {
  if (!active || !payload || payload.length === 0) return null;
  const titre = formatLibelle ? formatLibelle(label) : String(label ?? '');
  return (
    <div className="chart-tooltip" role="status">
      {titre && <div className="chart-tooltip__titre">{titre}</div>}
      {payload
        .filter((p) => p.value !== undefined && p.value !== null)
        .map((p) => (
          <div key={String(p.dataKey ?? p.name)} className="chart-tooltip__ligne">
            <span
              className="chart-tooltip__cle"
              style={{ background: p.color ?? p.fill ?? 'var(--axa-blue)' }}
              aria-hidden
            />
            <strong>
              {formatValeur ? formatValeur(Number(p.value), String(p.dataKey)) : String(p.value)}
            </strong>
            <span className="muted">{String(p.name ?? p.dataKey)}</span>
          </div>
        ))}
    </div>
  );
}
