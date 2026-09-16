// Ventilation par entité (distributeurs pour le siège, assurés pour un distributeur) :
// barres horizontales empilées Acceptées / En instruction / Refusées, même palette et même ordre que le mensuel.
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { LigneDistributeur } from '@/api/types';
import { InfoBulle } from '../Tooltip';
import { CHROME, COULEUR_BROUILLON, SERIES_DECISION } from '../palette';
import { Legende, TICK, formeBarreHorizontale } from './communs';

const SERIES = [
  ...SERIES_DECISION,
  { cle: 'brouillons', libelle: 'Brouillons', couleur: COULEUR_BROUILLON },
] as const;
const ORDRE = SERIES.map((s) => s.cle);

export function TopDistributeurs({ lignes }: { lignes: LigneDistributeur[] }) {
  return (
    <>
      <div className="chart-zone" style={{ height: 48 + lignes.length * 40 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={lignes}
            layout="vertical"
            margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
            barCategoryGap="30%"
          >
            <CartesianGrid horizontal={false} stroke={CHROME.grille} />
            <XAxis
              type="number"
              allowDecimals={false}
              tick={TICK}
              axisLine={{ stroke: CHROME.axe }}
              tickLine={false}
            />
            <YAxis type="category" dataKey="nom" width={170} tick={TICK} axisLine={false} tickLine={false} />
            <Tooltip cursor={{ fill: '#E2EFFF' }} content={<InfoBulle />} />
            {SERIES.map((s) => (
              <Bar
                key={s.cle}
                dataKey={s.cle}
                name={s.libelle}
                stackId="dist"
                fill={s.couleur}
                maxBarSize={22}
                isAnimationActive={false}
                shape={formeBarreHorizontale(ORDRE.slice(ORDRE.indexOf(s.cle) + 1))}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
      <Legende items={SERIES} />
    </>
  );
}
