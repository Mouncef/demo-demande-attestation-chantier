/* eslint-disable react-refresh/only-export-components -- fabriques de formes et helpers colocalisés */
// Éléments partagés par les graphiques : forme des segments (gap de 2 px, extrémité arrondie), légende.
import type { ReactElement } from 'react';
import { CHROME } from '../palette';

interface FormeProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  fill?: string;
  payload?: Record<string, number | string>;
}

/**
 * Segment d'une colonne empilée (barres verticales). Un gap de 2 px en couleur de surface sépare les
 * segments ; seul le segment visible le plus haut de la pile reçoit l'extrémité arrondie (4 px), la base
 * reste carrée. `suivantes` = clés des séries empilées au-dessus de celle-ci (ordre de la pile).
 */
export function formeSegmentVertical(suivantes: readonly string[]) {
  return function Segment({
    x = 0,
    y = 0,
    width = 0,
    height = 0,
    fill,
    payload,
  }: FormeProps): ReactElement | null {
    if (height <= 0 || width <= 0) return null;
    const estSommet = suivantes.every((cle) => !Number(payload?.[cle]));
    const r = estSommet ? Math.min(4, width / 2, height) : 0;
    const gap = 1; // 1 px de chaque côté → 2 px entre deux segments
    const yy = y + gap;
    const h = Math.max(0, height - gap * 2);
    const d = `M${x},${yy + h} V${yy + r} Q${x},${yy} ${x + r},${yy} H${x + width - r} Q${x + width},${yy} ${x + width},${yy + r} V${yy + h} Z`;
    return <path d={d} fill={fill} />;
  };
}

/** Barre horizontale (layout « vertical » de Recharts) : extrémité droite arrondie, base gauche carrée, gap 2 px. */
export function formeBarreHorizontale(suivantes: readonly string[] = []) {
  return function Barre({
    x = 0,
    y = 0,
    width = 0,
    height = 0,
    fill,
    payload,
  }: FormeProps): ReactElement | null {
    if (height <= 0 || width <= 0) return null;
    const estExtremite = suivantes.every((cle) => !Number(payload?.[cle]));
    const r = estExtremite ? Math.min(4, height / 2, width) : 0;
    const gap = 1;
    const xx = x + gap;
    const w = Math.max(0, width - gap * 2);
    const d = `M${xx},${y} H${xx + w - r} Q${xx + w},${y} ${xx + w},${y + r} V${y + height - r} Q${xx + w},${y + height} ${xx + w - r},${y + height} H${xx} Z`;
    return <path d={d} fill={fill} />;
  };
}

/** Légende (toujours présente dès deux séries) : swatch rectangulaire + libellé en texte secondaire. */
export function Legende({ items }: { items: readonly { libelle: string; couleur: string }[] }) {
  return (
    <div className="chart-legende" aria-label="Légende">
      {items.map((i) => (
        <span key={i.libelle} className="chart-legende__item">
          <span className="chart-legende__swatch" style={{ background: i.couleur }} aria-hidden />
          {i.libelle}
        </span>
      ))}
    </div>
  );
}

/** Style commun des ticks d'axes (texte en tokens, jamais en couleur de série). */
export const TICK = { fill: CHROME.texteSecondaire, fontSize: 12 } as const;
