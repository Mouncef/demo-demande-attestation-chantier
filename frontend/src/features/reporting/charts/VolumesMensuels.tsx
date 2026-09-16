/* eslint-disable react-refresh/only-export-components -- fabriques de formes et helpers colocalisés */
// Colonnes empilées par mois de création : Acceptées / En instruction / Refusées (+ brouillons en neutre).
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { LigneMensuelle } from '@/api/types';
import { InfoBulle } from '../Tooltip';
import { CHROME, COULEUR_BROUILLON, SERIES_DECISION, formatMois } from '../palette';
import { Legende, TICK, formeSegmentVertical } from './communs';

const ORDRE = [...SERIES_DECISION.map((s) => s.cle), 'brouillons'] as const;
const LIBELLES: Record<string, string> = Object.fromEntries([
  ...SERIES_DECISION.map((s) => [s.cle, s.libelle]),
  ['brouillons', 'Brouillons'],
]);

export function VolumesMensuels({ lignes }: { lignes: LigneMensuelle[] }) {
  const avecBrouillons = lignes.some((l) => l.brouillons > 0);
  const series = [
    ...SERIES_DECISION.map((s) => ({ cle: s.cle, libelle: s.libelle, couleur: s.couleur })),
    ...(avecBrouillons ? [{ cle: 'brouillons', libelle: 'Brouillons', couleur: COULEUR_BROUILLON }] : []),
  ];
  const derniere = series[series.length - 1].cle;
  return (
    <>
      <div className="chart-zone chart-zone--haute">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={lignes} margin={{ top: 24, right: 8, left: -16, bottom: 0 }} barCategoryGap="35%">
            <CartesianGrid vertical={false} stroke={CHROME.grille} />
            <XAxis
              dataKey="mois"
              tickFormatter={formatMois}
              tick={TICK}
              axisLine={{ stroke: CHROME.axe }}
              tickLine={false}
            />
            <YAxis allowDecimals={false} tick={TICK} axisLine={false} tickLine={false} />
            <Tooltip
              cursor={{ fill: '#E2EFFF' }}
              content={<InfoBulle formatLibelle={(v) => formatMois(String(v))} />}
            />
            {series.map((s, i) => (
              <Bar
                key={s.cle}
                dataKey={s.cle}
                name={s.libelle}
                stackId="mois"
                fill={s.couleur}
                maxBarSize={24}
                isAnimationActive={false}
                shape={formeSegmentVertical(ORDRE.slice(ORDRE.indexOf(s.cle as (typeof ORDRE)[number]) + 1))}
              >
                {/* Libellé direct sélectif : le total au sommet de chaque colonne uniquement. */}
                {s.cle === derniere && i === series.length - 1 && (
                  <LabelList
                    dataKey="total"
                    position="top"
                    offset={6}
                    fill={CHROME.texte}
                    fontSize={12}
                    fontWeight={600}
                  />
                )}
              </Bar>
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legende items={series} />
    </>
  );
}

/** Lignes de la vue tableau. */
export function tableauVolumes(lignes: LigneMensuelle[]) {
  return {
    colonnes: [
      { cle: 'mois', libelle: 'Mois' },
      ...ORDRE.map((cle) => ({ cle, libelle: LIBELLES[cle], numerique: true })),
      { cle: 'total', libelle: 'Total', numerique: true },
    ],
    lignes: lignes.map((l) => ({ ...l, mois: formatMois(l.mois) })),
  };
}
