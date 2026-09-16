// Barres horizontales à série unique (répartition nominale ou ordinale) : valeur au bout de la barre.
import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { InfoBulle } from '../Tooltip';
import { CHROME, COULEUR_SERIE } from '../palette';
import { TICK, formeBarreHorizontale } from './communs';

export interface LigneBarre {
  libelle: string;
  valeur: number;
  /** Couleur explicite (rampe ordinale) ; sinon la série unique. */
  couleur?: string;
  /** Texte secondaire affiché après la valeur (ex. taux de conversion). */
  detail?: string;
}

export function BarresHorizontales({ lignes, hauteur = 220 }: { lignes: LigneBarre[]; hauteur?: number }) {
  const max = Math.max(1, ...lignes.map((l) => l.valeur));
  return (
    <div className="chart-zone" style={{ height: hauteur }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={lignes}
          layout="vertical"
          margin={{ top: 4, right: 96, left: 8, bottom: 4 }}
          barCategoryGap="30%"
        >
          <XAxis type="number" hide domain={[0, max]} allowDecimals={false} />
          <YAxis
            type="category"
            dataKey="libelle"
            width={150}
            tick={TICK}
            axisLine={{ stroke: CHROME.axe }}
            tickLine={false}
          />
          <Tooltip cursor={{ fill: '#E2EFFF' }} content={<InfoBulle />} />
          <Bar
            dataKey="valeur"
            name="Demandes"
            maxBarSize={22}
            isAnimationActive={false}
            shape={formeBarreHorizontale()}
          >
            {lignes.map((l) => (
              <Cell key={l.libelle} fill={l.couleur ?? COULEUR_SERIE} />
            ))}
            <LabelList
              dataKey="valeur"
              position="right"
              offset={8}
              fill={CHROME.texte}
              fontSize={12}
              fontWeight={600}
              formatter={(v: unknown) => {
                const ligne = lignes.find((l) => l.valeur === Number(v));
                return ligne?.detail ? `${v} (${ligne.detail})` : String(v);
              }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
