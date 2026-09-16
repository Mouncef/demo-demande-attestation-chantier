// Écran 7 : résultat de l'analyse IA (simulée) – statut, score, liste des incohérences cliquables.
import type { AnalyseIA } from '@/api/types';
import { formatDateHeure } from '@/lib/format';
import { Alert, Badge } from '@/design-system/components';

const COULEUR = { MAJEURE: 'red', MOYENNE: 'orange', MINEURE: 'blue' } as const;

export function AnalysePanel({
  analyse,
  aJour,
  onCliquer,
}: {
  analyse: AnalyseIA;
  aJour: boolean;
  onCliquer: (extrait: string | null) => void;
}) {
  const r = analyse.resultat;
  return (
    <div>
      {!aJour && (
        <Alert type="warning">
          Le contenu a changé depuis cette analyse : relancez l'analyse avant validation.
        </Alert>
      )}
      <Alert type={r.statut === 'COHERENT' ? 'success' : 'danger'}>
        <strong>{r.statut === 'COHERENT' ? '✅ Cohérent' : '⚠️ Incohérences détectées'}</strong> — score de
        cohérence {r.score}/100
        <div className="small">
          {r.resume} · {formatDateHeure(analyse.created_at)} par {analyse.created_by}
        </div>
      </Alert>
      {r.incoherences.length > 0 && (
        <ul className="checklist" style={{ marginBottom: '1rem' }}>
          {r.incoherences.map((i, idx) => (
            <li
              key={`${i.code}-${idx}`}
              className="incoherence"
              onClick={() => onCliquer(i.extrait)}
              role="button"
              tabIndex={0}
              title={i.extrait ? 'Voir dans le document' : undefined}
            >
              <Badge couleur={COULEUR[i.severite]}>{i.severite}</Badge>
              <div>
                <div>
                  <strong>{i.code.replaceAll('_', ' ')}</strong>
                </div>
                <div className="small">{i.message}</div>
                {i.attendu && <div className="small muted">Attendu : {i.attendu}</div>}
              </div>
            </li>
          ))}
        </ul>
      )}
      <details>
        <summary className="small muted">{r.controles_ok.length} contrôle(s) satisfait(s)</summary>
        <div className="chips mt-1">
          {r.controles_ok.map((c) => (
            <Badge key={c} couleur="green">
              {c.replaceAll('_', ' ')}
            </Badge>
          ))}
        </div>
      </details>
    </div>
  );
}
