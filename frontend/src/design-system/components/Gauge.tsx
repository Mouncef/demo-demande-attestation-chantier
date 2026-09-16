import type { NiveauRisque } from '@/api/types';
import { BadgeNiveau } from './Badge';

/** Jauge de score 0-100 avec zones FAIBLE / MODÉRÉ / ÉLEVÉ (seuils 30 et 65). */
export function Gauge({ score, niveau }: { score: number; niveau: NiveauRisque }) {
  return (
    <div
      className="gauge"
      role="meter"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={score}
      aria-label="Score de risque"
    >
      <div className="gauge__bar">
        <div className="gauge__cursor" style={{ left: `${Math.min(100, Math.max(0, score))}%` }} />
      </div>
      <div className="gauge__score">{score}/100</div>
      <BadgeNiveau niveau={niveau} />
    </div>
  );
}
