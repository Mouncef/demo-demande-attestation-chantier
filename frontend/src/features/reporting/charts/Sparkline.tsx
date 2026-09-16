// Mini-courbe (2 px) des totaux mensuels pour la tuile KPI « Demandes » : dernier point marqué (r = 4, anneau blanc).
import { Line, LineChart, ResponsiveContainer } from 'recharts';
import type { LigneMensuelle } from '@/api/types';
import { COULEUR_SERIE } from '../palette';

export function Sparkline({ lignes }: { lignes: LigneMensuelle[] }) {
  if (lignes.length < 2) return null;
  const dernier = lignes.length - 1;
  return (
    <div className="kpi__spark" aria-hidden>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={lignes} margin={{ top: 6, right: 6, left: 6, bottom: 6 }}>
          <Line
            type="monotone"
            dataKey="total"
            stroke={COULEUR_SERIE}
            strokeWidth={2}
            isAnimationActive={false}
            dot={(props: { cx?: number; cy?: number; index?: number }) =>
              props.index === dernier ? (
                <circle
                  key="dernier"
                  cx={props.cx}
                  cy={props.cy}
                  r={4}
                  fill={COULEUR_SERIE}
                  stroke="#fff"
                  strokeWidth={2}
                />
              ) : (
                <g key={`vide-${props.index}`} />
              )
            }
            activeDot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
