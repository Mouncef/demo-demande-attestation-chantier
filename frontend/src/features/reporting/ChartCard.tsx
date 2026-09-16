// Carte de graphique : titre, sous-titre, bascule Graphique / Tableau (équivalent accessible) et état vide.
import { useState, type ReactNode } from 'react';

interface Colonne {
  cle: string;
  libelle: string;
  numerique?: boolean;
}

interface Props {
  titre: string;
  sousTitre?: string;
  vide: boolean;
  /** Vue tableau : colonnes et lignes (chaque graphique a son équivalent tabulaire). */
  colonnes: Colonne[];
  lignes: Record<string, string | number>[];
  /** Le rendu précédent est conservé à opacité réduite pendant un rechargement. */
  rechargement?: boolean;
  children: ReactNode;
}

export function ChartCard({ titre, sousTitre, vide, colonnes, lignes, rechargement, children }: Props) {
  const [vue, setVue] = useState<'graphique' | 'tableau'>('graphique');
  return (
    <section className={`card chart-card ${rechargement ? 'chart-card--rechargement' : ''}`}>
      <div className="chart-card__entete">
        <div>
          <h2>{titre}</h2>
          {sousTitre && (
            <p className="small muted" style={{ margin: 0 }}>
              {sousTitre}
            </p>
          )}
        </div>
        {!vide && (
          <div className="chart-card__bascule" role="tablist" aria-label="Mode d'affichage">
            <button
              type="button"
              role="tab"
              aria-selected={vue === 'graphique'}
              onClick={() => setVue('graphique')}
            >
              Graphique
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={vue === 'tableau'}
              onClick={() => setVue('tableau')}
            >
              Tableau
            </button>
          </div>
        )}
      </div>
      {vide ? (
        <div className="empty">Pas encore de données sur cette période.</div>
      ) : vue === 'graphique' ? (
        children
      ) : (
        <div className="table-wrap">
          <table className="table chart-card__table">
            <thead>
              <tr>
                {colonnes.map((c) => (
                  <th key={c.cle} className={c.numerique ? 'num' : undefined}>
                    {c.libelle}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {lignes.map((l, i) => (
                <tr key={i}>
                  {colonnes.map((c) => (
                    <td key={c.cle} className={c.numerique ? 'num' : undefined}>
                      {l[c.cle]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
