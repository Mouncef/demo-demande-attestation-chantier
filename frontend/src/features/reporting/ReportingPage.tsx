// Écran 9 : reporting – filtres de période, KPI, graphiques adaptés à chaque lecture (skill dataviz) :
// colonnes empilées mensuelles, barres horizontales par statut, rampe ordinale pour le risque, entonnoir du
// circuit d'attestation, top distributeurs (siège). Chaque carte a sa vue tableau.
import { useState } from 'react';
import { useReporting } from '@/api/demandes';
import type { NiveauRisque, PeriodeReporting, Statut } from '@/api/types';
import { useAuth } from '@/features/auth/AuthContext';
import { LIBELLES_NIVEAU, LIBELLES_STATUT } from '@/lib/libelles';
import { Kpi, Spinner } from '@/design-system/components';
import { ChartCard } from './ChartCard';
import { BarresHorizontales } from './charts/BarresHorizontales';
import { Sparkline } from './charts/Sparkline';
import { TopDistributeurs } from './charts/TopDistributeurs';
import { VolumesMensuels, tableauVolumes } from './charts/VolumesMensuels';
import { COULEUR_NON_EVALUE, RAMPE_ORDINALE } from './palette';
import './reporting.css';

const PERIODES: { valeur: PeriodeReporting; libelle: string }[] = [
  { valeur: '30', libelle: '30 derniers jours' },
  { valeur: '90', libelle: '90 derniers jours' },
  { valeur: '365', libelle: '12 derniers mois' },
  { valeur: 'tout', libelle: 'Tout' },
];
const ORDRE_STATUTS: Statut[] = ['BROUILLON', 'EN_COURS', 'A_COMPLETER', 'TRAITE'];
const ORDRE_NIVEAUX: NiveauRisque[] = ['FAIBLE', 'MODERE', 'ELEVE'];

const pct = (part: number, total: number) => (total ? `${Math.round((100 * part) / total)} %` : '—');
/** Délai en jours : « — » sans donnée, « < 1 j » le jour même, sinon la valeur. */
const jours = (v: number | null) => (v === null ? '—' : v < 1 ? '< 1 j' : `${v} j`);

export function ReportingPage() {
  const { utilisateur } = useAuth();
  const estSiege = utilisateur?.role === 'SIEGE';
  const [periode, setPeriode] = useState<PeriodeReporting>('tout');
  const { data, isLoading, isFetching } = useReporting(periode);
  if (isLoading || !data) return <Spinner label="Chargement du reporting…" />;

  const statuts = ORDRE_STATUTS.map((s) => ({ libelle: LIBELLES_STATUT[s], valeur: data.par_statut[s] }));
  const niveaux = [
    ...ORDRE_NIVEAUX.map((n, i) => ({
      libelle: LIBELLES_NIVEAU[n],
      valeur: data.par_niveau_risque[n],
      couleur: RAMPE_ORDINALE[i],
    })),
    { libelle: 'Non évalué', valeur: data.par_niveau_risque.NON_EVALUE, couleur: COULEUR_NON_EVALUE },
  ];
  const c = data.circuit_attestation;
  const circuit = [
    { libelle: 'Demandes acceptées', valeur: c.acceptees, couleur: RAMPE_ORDINALE[0] },
    {
      libelle: 'Projets soumis',
      valeur: c.projets_soumis,
      couleur: RAMPE_ORDINALE[1],
      detail: pct(c.projets_soumis, c.acceptees),
    },
    {
      libelle: 'Attestations établies',
      valeur: c.attestations_etablies,
      couleur: RAMPE_ORDINALE[2],
      detail: pct(c.attestations_etablies, c.acceptees),
    },
  ];
  const volumes = tableauVolumes(data.par_mois);
  const rechargement = isFetching;

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Reporting</h1>
          <p className="muted" style={{ margin: 0 }}>
            {estSiege
              ? 'Ensemble des demandes'
              : `Vos demandes${utilisateur?.organisation ? ` – ${utilisateur.organisation}` : ''}`}
          </p>
        </div>
      </div>

      {/* Une seule ligne de filtres : la période s'applique à toutes les cartes. */}
      <div className="reporting-filtres" role="group" aria-label="Période">
        <span className="small muted">Période</span>
        <div className="chips">
          {PERIODES.map((p) => (
            <button
              key={p.valeur}
              type="button"
              className="chip"
              aria-pressed={periode === p.valeur}
              onClick={() => setPeriode(p.valeur)}
            >
              {p.libelle}
            </button>
          ))}
        </div>
      </div>

      <div className="grid-3 mb-2">
        <div className="kpi kpi--sparkline">
          <div>
            <div className="kpi__value">{data.total}</div>
            <div className="kpi__label">Demandes</div>
          </div>
          <Sparkline lignes={data.par_mois} />
        </div>
        <Kpi
          valeur={data.a_traiter}
          label={estSiege ? 'À traiter par le siège' : 'À traiter par vous'}
          couleur={data.a_traiter > 0 ? 'var(--axa-red)' : undefined}
        />
        <Kpi
          valeur={data.taux_acceptation !== null ? `${data.taux_acceptation} %` : '—'}
          label="Taux d'acceptation"
        />
      </div>
      <div className="grid-3 mb-2">
        <Kpi valeur={jours(data.delai_moyen_decision_jours)} label="Délai moyen de décision" />
        <Kpi
          valeur={jours(data.delai_moyen_attestation_jours)}
          label="Délai moyen d'établissement de l'attestation"
        />
        <Kpi valeur={c.attestations_etablies} label="Attestations établies" />
      </div>

      <div className="reporting-grille">
        <div className="chart-card--large">
          <ChartCard
            titre="Demandes par mois"
            sousTitre="Mois de création, ventilées selon leur situation actuelle"
            vide={data.par_mois.length === 0}
            colonnes={volumes.colonnes}
            lignes={volumes.lignes}
            rechargement={rechargement}
          >
            <VolumesMensuels lignes={data.par_mois} />
          </ChartCard>
        </div>

        <ChartCard
          titre="Répartition par statut"
          sousTitre="Dans l'ordre du cycle de vie"
          vide={data.total === 0}
          colonnes={[
            { cle: 'libelle', libelle: 'Statut' },
            { cle: 'valeur', libelle: 'Demandes', numerique: true },
          ]}
          lignes={statuts}
          rechargement={rechargement}
        >
          <BarresHorizontales lignes={statuts} hauteur={200} />
        </ChartCard>

        <ChartCard
          titre="Niveau de risque"
          sousTitre="Score figé au dernier envoi au siège"
          vide={data.total === 0}
          colonnes={[
            { cle: 'libelle', libelle: 'Niveau' },
            { cle: 'valeur', libelle: 'Demandes', numerique: true },
          ]}
          lignes={niveaux}
          rechargement={rechargement}
        >
          <BarresHorizontales lignes={niveaux} hauteur={200} />
        </ChartCard>

        <ChartCard
          titre="Circuit d'attestation"
          sousTitre="Des demandes acceptées aux attestations définitives établies"
          vide={c.acceptees === 0}
          colonnes={[
            { cle: 'libelle', libelle: 'Étape' },
            { cle: 'valeur', libelle: 'Demandes', numerique: true },
            { cle: 'detail', libelle: 'Conversion' },
          ]}
          lignes={circuit.map((l) => ({ ...l, detail: l.detail ?? '100 %' }))}
          rechargement={rechargement}
        >
          <BarresHorizontales lignes={circuit} hauteur={170} />
          <p className="entonnoir-etape">Taux calculés par rapport aux demandes acceptées.</p>
        </ChartCard>

        {(data.par_distributeur ?? data.par_assure) && (
          <ChartCard
            titre={estSiege ? 'Distributeurs les plus actifs' : 'Assurés les plus fréquents'}
            sousTitre={
              estSiege
                ? 'Demandes par distributeur, selon leur situation'
                : 'Vos demandes par assuré, selon leur situation'
            }
            vide={(data.par_distributeur ?? data.par_assure ?? []).length === 0}
            colonnes={[
              { cle: 'nom', libelle: estSiege ? 'Distributeur' : 'Assuré' },
              { cle: 'acceptees', libelle: 'Acceptées', numerique: true },
              { cle: 'en_instruction', libelle: 'En instruction', numerique: true },
              { cle: 'refusees', libelle: 'Refusées', numerique: true },
              { cle: 'brouillons', libelle: 'Brouillons', numerique: true },
              { cle: 'total', libelle: 'Total', numerique: true },
            ]}
            lignes={(data.par_distributeur ?? data.par_assure ?? []).map((d) => ({ ...d }))}
            rechargement={rechargement}
          >
            <TopDistributeurs lignes={data.par_distributeur ?? data.par_assure ?? []} />
          </ChartCard>
        )}
      </div>
    </>
  );
}
