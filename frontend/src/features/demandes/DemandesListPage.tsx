// Écran 1 : liste des demandes avec filtres statut / décision, recherche, tri, pagination, relance.
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCreerDemande, useDemandes, useSupprimerDemande } from '@/api/demandes';
import type { Decision, DemandeListe, Statut } from '@/api/types';
import { useAuth } from '@/features/auth/AuthContext';
import { formatDate, formatMontant } from '@/lib/format';
import { LIBELLES_DECISION, LIBELLES_STATUT } from '@/lib/libelles';
import {
  BadgeDecision,
  BadgeNiveau,
  BadgeStatut,
  Button,
  Card,
  EmptyState,
  Input,
  Modal,
  Pagination,
  TAILLES_PAGE,
  Select,
  Spinner,
  useToast,
} from '@/design-system/components';
import { RelanceButton } from './RelanceButton';

const STATUTS = Object.keys(LIBELLES_STATUT) as Statut[];
const DECISIONS = Object.keys(LIBELLES_DECISION) as NonNullable<Decision>[];

export function DemandesListPage() {
  const { utilisateur } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [statuts, setStatuts] = useState<Statut[]>([]);
  const [decisions, setDecisions] = useState<NonNullable<Decision>[]>([]);
  const [recherche, setRecherche] = useState('');
  const [tri, setTri] = useState('-updated_at');
  const [page, setPage] = useState(1);
  // Lignes par page : 5 par défaut, préférence mémorisée dans le navigateur.
  const [taille, setTaille] = useState(() => lireTaillePage());
  const { data, isLoading, isError } = useDemandes({
    statut: statuts,
    decision: decisions,
    search: recherche,
    ordering: tri,
    page,
    pageSize: taille,
  });
  const creer = useCreerDemande();
  const supprimer = useSupprimerDemande();
  // Brouillon dont la suppression est demandée (confirmation avant action irréversible).
  const [aSupprimer, setASupprimer] = useState<DemandeListe | null>(null);

  const basculer = <T extends string>(liste: T[], v: T, set: (l: T[]) => void) => {
    set(liste.includes(v) ? liste.filter((x) => x !== v) : [...liste, v]);
    setPage(1);
  };

  const nouvelle = async () => {
    try {
      const d = await creer.mutateAsync();
      navigate(`/demandes/${d.id}`);
    } catch (e) {
      toast.erreur(e);
    }
  };

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Demandes d'attestation</h1>
          <p className="muted" style={{ margin: 0 }}>
            {utilisateur?.role === 'SIEGE' ? 'Toutes les demandes des distributeurs' : 'Vos demandes'}
          </p>
        </div>
        {utilisateur?.role === 'DISTRIBUTEUR' && (
          <Button onClick={nouvelle} chargement={creer.isPending}>
            ＋ Nouvelle demande
          </Button>
        )}
      </div>

      <Card variante="plain" className="mb-2">
        <div className="flex flex-wrap" style={{ gap: '1.25rem' }}>
          <div>
            <div className="small muted mb-2" style={{ marginBottom: 4 }}>
              Statut
            </div>
            <div className="chips">
              {STATUTS.map((s) => (
                <button
                  key={s}
                  type="button"
                  className="chip"
                  aria-pressed={statuts.includes(s)}
                  onClick={() => basculer(statuts, s, setStatuts)}
                >
                  {LIBELLES_STATUT[s]}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="small muted" style={{ marginBottom: 4 }}>
              Décision
            </div>
            <div className="chips">
              {DECISIONS.map((d) => (
                <button
                  key={d}
                  type="button"
                  className="chip"
                  aria-pressed={decisions.includes(d)}
                  onClick={() => basculer(decisions, d, setDecisions)}
                >
                  {LIBELLES_DECISION[d]}
                </button>
              ))}
            </div>
          </div>
          <div className="grow" style={{ minWidth: 220 }}>
            <div className="small muted" style={{ marginBottom: 4 }}>
              Recherche
            </div>
            <Input
              type="search"
              placeholder="Référence, assuré, chantier, contrat…"
              value={recherche}
              onChange={(e) => {
                setRecherche(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <div>
            <div className="small muted" style={{ marginBottom: 4 }}>
              Tri
            </div>
            <Select value={tri} onChange={(e) => setTri(e.target.value)}>
              <option value="-updated_at">Dernière activité</option>
              <option value="-created_at">Plus récentes</option>
              <option value="created_at">Plus anciennes</option>
              <option value="reference">Référence</option>
              <option value="statut">Statut</option>
            </Select>
          </div>
        </div>
      </Card>

      <Card variante="plain">
        {isLoading && <Spinner />}
        {isError && <EmptyState titre="Impossible de charger les demandes" />}
        {data && data.results.length === 0 && (
          <EmptyState titre="Aucune demande">
            {utilisateur?.role === 'DISTRIBUTEUR' && (
              <p>Créez votre première demande pour démarrer un Formulaire de Déclaration du Risque.</p>
            )}
          </EmptyState>
        )}
        {data && data.results.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Référence</th>
                  <th>Assuré</th>
                  <th>Chantier</th>
                  {utilisateur?.role === 'SIEGE' && <th>Distributeur</th>}
                  <th className="num">Coût total</th>
                  <th>Risque</th>
                  <th>Statut</th>
                  <th>Décision</th>
                  <th>Envoyée le</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((d) => (
                  <tr key={d.id} className="clickable" onClick={() => navigate(`/demandes/${d.id}`)}>
                    <td>
                      <strong>{d.reference}</strong>
                    </td>
                    <td>{d.assure_nom ?? <span className="muted">—</span>}</td>
                    <td>
                      {d.chantier_nom ?? <span className="muted">—</span>}
                      {d.chantier_ville && <div className="small muted">{d.chantier_ville}</div>}
                    </td>
                    {utilisateur?.role === 'SIEGE' && <td>{d.distributeur.nom_affichage}</td>}
                    <td className="num">{formatMontant(d.cout_total)}</td>
                    <td>
                      <BadgeNiveau niveau={d.niveau_risque} />
                    </td>
                    <td>
                      <BadgeStatut statut={d.statut} />
                    </td>
                    <td>
                      <BadgeDecision decision={d.decision} />
                    </td>
                    <td>{formatDate(d.submitted_at)}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <div className="actions" style={{ justifyContent: 'flex-end' }}>
                        {d.actions_possibles.includes('relancer') && (
                          <RelanceButton
                            demandeId={d.id}
                            prochaine={d.prochaine_relance_possible}
                            taille="sm"
                          />
                        )}
                        {d.actions_possibles.includes('supprimer') && (
                          <Button
                            variante="danger"
                            taille="sm"
                            onClick={() => setASupprimer(d)}
                            aria-label={`Supprimer le brouillon ${d.reference}`}
                          >
                            🗑 Supprimer
                          </Button>
                        )}
                        <Button
                          variante="secondary"
                          taille="sm"
                          onClick={() => navigate(`/demandes/${d.id}`)}
                        >
                          Ouvrir
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {data && (
          <Pagination
            page={page}
            total={data.count}
            taille={taille}
            onChange={setPage}
            onTailleChange={(t) => {
              setTaille(t);
              memoriserTaillePage(t);
              setPage(1);
            }}
          />
        )}
      </Card>

      <Modal
        ouvert={aSupprimer !== null}
        titre="Supprimer le brouillon"
        onFermer={() => setASupprimer(null)}
        pied={
          <>
            <Button variante="secondary" onClick={() => setASupprimer(null)}>
              Annuler
            </Button>
            <Button
              variante="danger"
              chargement={supprimer.isPending}
              onClick={() =>
                aSupprimer &&
                supprimer.mutate(aSupprimer.id, {
                  onSuccess: () => {
                    toast.notifier(`Brouillon ${aSupprimer.reference} supprimé.`, 'success');
                    setASupprimer(null);
                  },
                  onError: (e) => toast.erreur(e),
                })
              }
            >
              Supprimer définitivement
            </Button>
          </>
        }
      >
        <p>
          Le brouillon <strong>{aSupprimer?.reference}</strong>
          {aSupprimer?.assure_nom ? ` (${aSupprimer.assure_nom})` : ''}, son FDR et ses pièces seront
          supprimés. Cette action est irréversible.
        </p>
      </Modal>
    </>
  );
}

const CLE_TAILLE_PAGE = 'demandes.taillePage';
const TAILLE_PAGE_DEFAUT = 5;

/** Préférence d'affichage propre au navigateur (stockage tolérant aux environnements sans localStorage). */
function lireTaillePage(): number {
  try {
    const v = Number(localStorage.getItem(CLE_TAILLE_PAGE));
    return TAILLES_PAGE.includes(v as (typeof TAILLES_PAGE)[number]) ? v : TAILLE_PAGE_DEFAUT;
  } catch {
    return TAILLE_PAGE_DEFAUT;
  }
}

function memoriserTaillePage(taille: number): void {
  try {
    localStorage.setItem(CLE_TAILLE_PAGE, String(taille));
  } catch {
    /* stockage indisponible : préférence non mémorisée */
  }
}
