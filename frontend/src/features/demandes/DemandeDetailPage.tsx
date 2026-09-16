// Détail d'une demande : parcours en étapes pour le distributeur (FDR, historique), vue dossier pour le siège.
import { useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useDemande, useHistorique, useSupprimerDemande } from '@/api/demandes';
import type { DemandeDetail } from '@/api/types';
import { useAuth } from '@/features/auth/AuthContext';
import { FdrForm } from '@/features/fdr/FdrForm';
import { formatDateHeure, formatMontant } from '@/lib/format';
import {
  BadgeDecision,
  BadgeNiveau,
  BadgeStatut,
  Button,
  Card,
  EmptyState,
  Modal,
  Spinner,
  StepNav,
  Stepper,
  Tabs,
  useToast,
} from '@/design-system/components';

type Etape = 'fdr' | 'historique';

export function DemandeDetailPage() {
  const { id = '' } = useParams();
  const { utilisateur } = useAuth();
  const { data: demande, isLoading, isError } = useDemande(id);
  if (isLoading) return <Spinner label="Chargement de la demande…" />;
  if (isError || !demande) return <EmptyState titre="Demande introuvable ou inaccessible" />;
  return utilisateur?.role === 'SIEGE' ? (
    <VueSiege demande={demande} />
  ) : (
    <VueDistributeur demande={demande} />
  );
}

function EnTete({ demande, children }: { demande: DemandeDetail; children?: React.ReactNode }) {
  const navigate = useNavigate();
  return (
    <div className="page-header">
      <div>
        <Button variante="ghost" taille="sm" onClick={() => navigate('/demandes')}>
          ← Retour à la liste
        </Button>
        <h1 className="flex flex-wrap">
          {demande.reference}
          <BadgeStatut statut={demande.statut} />
          <BadgeDecision decision={demande.decision} />
          <BadgeNiveau niveau={demande.niveau_risque} />
        </h1>
        <p className="muted" style={{ margin: 0 }}>
          {demande.assure_nom ?? 'Assuré non renseigné'} · {demande.chantier_nom ?? 'Chantier non renseigné'}
          {demande.chantier_ville ? ` (${demande.chantier_ville})` : ''} · {formatMontant(demande.cout_total)}
        </p>
      </div>
      <div className="actions">{children}</div>
    </div>
  );
}

function VueDistributeur({ demande }: { demande: DemandeDetail }) {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const supprimer = useSupprimerDemande();
  const [confirmerSuppression, setConfirmerSuppression] = useState(false);
  const peut = (a: string) => demande.actions_possibles.includes(a as never);
  const editable = peut('modifier_fdr');

  const etape: Etape = (params.get('etape') as Etape) || 'fdr';
  const aller = (e: string) => setParams({ etape: e });
  const etapes = [
    { cle: 'fdr', libelle: 'Formulaire FDR' },
    { cle: 'historique', libelle: 'Historique' },
  ];
  const ordre = etapes.map((e) => e.cle);
  const index = ordre.indexOf(etape);
  const precedent = index > 0 ? () => aller(ordre[index - 1]) : undefined;
  const suivant = index >= 0 && index < ordre.length - 1 ? () => aller(ordre[index + 1]) : undefined;

  return (
    <>
      <EnTete demande={demande}>
        {peut('supprimer') && (
          <Button variante="danger" onClick={() => setConfirmerSuppression(true)}>
            🗑 Supprimer
          </Button>
        )}
      </EnTete>

      <Stepper etapes={etapes} courante={etape} onChange={aller} />

      {etape === 'fdr' && (
        <FdrForm demande={demande} lectureSeule={!editable} onPrecedent={precedent} onSuivant={suivant} />
      )}
      {etape === 'historique' && <HistoriquePanel demande={demande} />}
      {etape !== 'fdr' && <StepNav onPrecedent={precedent} onSuivant={suivant} />}

      <Modal
        ouvert={confirmerSuppression}
        titre="Supprimer le brouillon"
        onFermer={() => setConfirmerSuppression(false)}
        pied={
          <>
            <Button variante="secondary" onClick={() => setConfirmerSuppression(false)}>
              Annuler
            </Button>
            <Button
              variante="danger"
              chargement={supprimer.isPending}
              onClick={() =>
                supprimer.mutate(demande.id, {
                  onSuccess: () => {
                    toast.notifier('Brouillon supprimé.', 'success');
                    navigate('/demandes');
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
        <p>Le brouillon {demande.reference} et son FDR seront supprimés. Cette action est irréversible.</p>
      </Modal>
    </>
  );
}

function VueSiege({ demande }: { demande: DemandeDetail }) {
  const [params, setParams] = useSearchParams();
  const onglet = params.get('onglet') ?? 'dossier';
  const onglets = [
    { cle: 'dossier', libelle: 'Dossier (FDR)' },
    { cle: 'historique', libelle: 'Historique' },
  ];
  return (
    <>
      <EnTete demande={demande} />
      <Card titre="Synthèse" variante="plain" className="mb-2">
        <div className="recap">
          <dl>
            <dt>Distributeur</dt>
            <dd>
              {demande.distributeur.nom_affichage}
              <div className="small muted">{demande.distributeur.organisation}</div>
            </dd>
            <dt>Créée le</dt>
            <dd>{formatDateHeure(demande.created_at)}</dd>
            <dt>Commentaire distributeur</dt>
            <dd>{demande.commentaire_distributeur || '—'}</dd>
          </dl>
        </div>
      </Card>
      <Tabs onglets={onglets} actif={onglet} onChange={(o) => setParams({ onglet: o })} />
      {onglet === 'dossier' && <FdrForm demande={demande} lectureSeule />}
      {onglet === 'historique' && <HistoriquePanel demande={demande} />}
    </>
  );
}

function HistoriquePanel({ demande }: { demande: DemandeDetail }) {
  const { data: historique } = useHistorique(demande.id);
  return (
    <Card titre="🕓 Historique des actions">
      {!historique ? (
        <Spinner />
      ) : (
        <ul className="timeline">
          {historique.map((h) => (
            <li key={h.id}>
              <strong>{h.action_libelle}</strong>{' '}
              <span className="small muted">
                — {formatDateHeure(h.created_at)} · {h.acteur.nom_affichage}
              </span>
              {h.commentaire && <div className="small">{h.commentaire}</div>}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
