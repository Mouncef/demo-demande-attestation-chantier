// Détail d'une demande : parcours en étapes pour le distributeur (FDR → risque & pièces →
// validation & envoi → attestation), vue instruction pour le siège, historique et soumissions.
import { lazy, Suspense, useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  cles,
  useCompletude,
  useDemande,
  useHistorique,
  useSoumissions,
  useSupprimerDemande,
} from '@/api/demandes';
import { telechargerFichier } from '@/api/client';
import type { DemandeDetail } from '@/api/types';
import { useAuth } from '@/features/auth/AuthContext';
import { FdrForm } from '@/features/fdr/FdrForm';
import { RisquePiecesStep } from '@/features/pieces/RisquePiecesStep';
import { ValidationStep } from '@/features/validation/ValidationStep';
import { TraitementPanel } from '@/features/siege/TraitementPanel';
import { formatDateHeure, formatMontant } from '@/lib/format';
import {
  Alert,
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
import { RelanceButton } from './RelanceButton';

// L'éditeur riche (TipTap) est chargé à la demande pour alléger le bundle initial.
const AttestationStepLazy = lazy(() =>
  import('@/features/attestation/AttestationStep').then((m) => ({ default: m.AttestationStep })),
);
function AttestationStep(props: React.ComponentProps<typeof AttestationStepLazy>) {
  return (
    <Suspense fallback={<Spinner label="Chargement de l'éditeur…" />}>
      <AttestationStepLazy {...props} />
    </Suspense>
  );
}

type Etape = 'fdr' | 'pieces' | 'validation' | 'attestation' | 'definitive' | 'historique';

/** Écran ciblé par une notification (`?vue=…`) → étape du parcours distributeur / onglet siège. */
const VUE_VERS_ETAPE: Record<string, Etape> = {
  projet: 'attestation',
  attestation: 'attestation',
  definitive: 'definitive',
};
const VUE_VERS_ONGLET: Record<string, string> = {
  projet: 'projet',
  attestation: 'projet',
  definitive: 'definitive',
};

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
  const { data: completude } = useCompletude(demande.id);
  const queryClient = useQueryClient();
  const supprimer = useSupprimerDemande();
  const [confirmerSuppression, setConfirmerSuppression] = useState(false);
  const peut = (a: string) => demande.actions_possibles.includes(a as never);
  const editable = peut('modifier_fdr');

  // --- Verrouillage séquentiel : une étape n'est accessible que si les précédentes sont valides. ---
  // Tant que la demande est éditable, on s'appuie sur la complétude calculée par le backend ; une fois
  // envoyée, le FDR et les pièces ont été validés à l'envoi : les étapes 1 à 3 sont acquises.
  const fdrValide = !editable || Boolean(completude?.fdr_valide);
  const dossierComplet = !editable || Boolean(completude?.complet);
  const envoyee = demande.nb_soumissions > 0;
  const acceptee = demande.decision === 'ACCEPTEE';
  const acces: Record<Etape, { ok: boolean; motif: string }> = {
    fdr: { ok: true, motif: '' },
    pieces: { ok: fdrValide, motif: 'Complétez et validez le formulaire FDR avant de passer aux pièces.' },
    validation: {
      ok: fdrValide && dossierComplet,
      motif: `Déposez toutes les pièces requises avant de continuer${completude?.manquants.length ? ` (${completude.manquants.length} manquante(s))` : ''}.`,
    },
    attestation: {
      ok: acceptee,
      motif: "Le projet d'attestation se prépare une fois la demande acceptée par le siège.",
    },
    definitive: {
      ok: acceptee,
      motif: "L'attestation définitive n'est disponible qu'une fois la demande acceptée.",
    },
    historique: { ok: true, motif: '' },
  };

  const etapeParDefaut: Etape = acceptee
    ? demande.etat_attestation === 'DEFINITIVE'
      ? 'definitive'
      : 'attestation'
    : editable
      ? 'fdr'
      : 'validation';
  const vue = params.get('vue');
  const etapeDemandee = (params.get('etape') as Etape) || (vue && VUE_VERS_ETAPE[vue]) || etapeParDefaut;
  const etape: Etape = acces[etapeDemandee]?.ok ? etapeDemandee : 'fdr';
  const allerDirect = (e: string) => setParams({ etape: e });
  /** Navigation contrôlée : refuse (avec explication) une étape dont les prérequis ne sont pas remplis. */
  const aller = (e: string) => {
    const cible = acces[e as Etape];
    if (cible && !cible.ok) {
      toast.notifier(cible.motif, 'error');
      return;
    }
    allerDirect(e);
  };

  // URL directe vers une étape verrouillée : on revient sur la première étape (une fois la complétude connue).
  useEffect(() => {
    if (editable && !completude) return;
    if (!acces[etapeDemandee]?.ok) setParams({ etape: 'fdr' }, { replace: true });
    else if (demande.statut === 'A_COMPLETER' && !params.get('etape'))
      setParams({ etape: 'fdr' }, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `acces` est recalculé à chaque rendu
  }, [etapeDemandee, editable, completude, demande.statut, params, setParams]);

  const etapes: { cle: string; libelle: string; termine?: boolean; desactive?: boolean }[] = [
    { cle: 'fdr', libelle: 'Formulaire FDR', termine: Boolean(completude?.fdr_valide) },
    {
      cle: 'pieces',
      libelle: 'Risque & pièces',
      termine: Boolean(completude?.fdr_valide && completude?.complet),
      desactive: !acces.pieces.ok,
    },
    { cle: 'validation', libelle: 'Validation & envoi', termine: envoyee, desactive: !acces.validation.ok },
    {
      cle: 'attestation',
      libelle: "Projet d'attestation",
      termine: demande.etat_attestation === 'PROJET_SOUMIS' || demande.etat_attestation === 'DEFINITIVE',
      desactive: !acces.attestation.ok,
    },
    ...(acceptee
      ? [
          {
            cle: 'definitive',
            libelle: 'Attestation définitive',
            termine: demande.etat_attestation === 'DEFINITIVE',
          },
        ]
      : []),
    { cle: 'historique', libelle: 'Historique' },
  ];

  // Navigation Précédent / Suivant entre les étapes (ordre du stepper), soumise au verrouillage.
  const ordre = etapes.map((e) => e.cle);
  const index = ordre.indexOf(etape);
  const precedent = index > 0 ? () => allerDirect(ordre[index - 1]) : undefined;
  const suivant = index >= 0 && index < ordre.length - 1 ? () => aller(ordre[index + 1]) : undefined;

  return (
    <>
      <EnTete demande={demande}>
        {peut('relancer') && (
          <RelanceButton demandeId={demande.id} prochaine={demande.prochaine_relance_possible} />
        )}
        {peut('supprimer') && (
          <Button variante="danger" onClick={() => setConfirmerSuppression(true)}>
            🗑 Supprimer
          </Button>
        )}
      </EnTete>

      {demande.statut === 'A_COMPLETER' && (
        <Alert type="warning">
          <strong>Le siège demande des éléments complémentaires :</strong> {demande.message_complements}
          <div className="small">
            Complétez le FDR et/ou les pièces, puis renvoyez la demande depuis l'étape « Validation & envoi ».
          </div>
        </Alert>
      )}
      {demande.statut === 'EN_COURS' && (
        <Alert type="info">
          Demande en cours d'instruction par le siège depuis le {formatDateHeure(demande.submitted_at)} (envoi
          n°{demande.nb_soumissions}). Vous pouvez préparer un projet d'attestation en attendant.
        </Alert>
      )}
      {demande.statut === 'TRAITE' && demande.decision === 'REFUSEE' && (
        <Alert type="danger">
          <strong>Demande refusée par le siège.</strong> Motif : {demande.motif_refus}
        </Alert>
      )}
      {demande.statut === 'TRAITE' && demande.decision === 'ACCEPTEE' && (
        <Alert type={demande.etat_attestation === 'PROJET_A_CORRIGER' ? 'warning' : 'success'}>
          <strong>Demande acceptée par le siège.</strong>{' '}
          {
            {
              AUCUNE: 'Préparez et soumettez votre projet d’attestation au siège.',
              PROJET_EN_COURS:
                'Votre projet d’attestation est en préparation : soumettez-le au siège lorsqu’il est prêt.',
              PROJET_SOUMIS:
                'Votre projet d’attestation est soumis : le siège établit l’attestation définitive.',
              PROJET_A_CORRIGER: 'Le siège vous a renvoyé le projet d’attestation pour correction.',
              DEFINITIVE: 'L’attestation définitive est disponible au téléchargement.',
            }[demande.etat_attestation]
          }
          {demande.commentaire_siege && (
            <div className="small">Commentaire du siège : {demande.commentaire_siege}</div>
          )}
        </Alert>
      )}

      <Stepper etapes={etapes} courante={etape} onChange={aller} />

      {etape === 'fdr' && (
        <FdrForm
          demande={demande}
          lectureSeule={!editable}
          erreursEnvoi={editable ? completude?.erreurs_fdr : {}}
          signalerErreurs={params.get('signaler') === '1'}
          onPrecedent={precedent}
          // Après « Valider et continuer », le FDR vient d'être validé et enregistré : on recharge la
          // complétude (sinon le verrouillage s'appuierait sur l'état d'avant l'enregistrement) puis on avance.
          onSuivant={async () => {
            await queryClient.refetchQueries({ queryKey: cles.completude(demande.id) });
            allerDirect('pieces');
          }}
        />
      )}
      {etape === 'pieces' && <RisquePiecesStep demande={demande} lectureSeule={!peut('gerer_pieces')} />}
      {etape === 'validation' && (
        <ValidationStep
          demande={demande}
          lectureSeule={!peut('envoyer')}
          onEnvoye={() => allerDirect('attestation')}
          // Depuis le récapitulatif, « corriger le FDR » ouvre le formulaire avec les erreurs signalées.
          onAllerEtape={(e) => (e === 'fdr' ? setParams({ etape: 'fdr', signaler: '1' }) : allerDirect(e))}
        />
      )}
      {etape === 'attestation' && (
        <AttestationStep demande={demande} kind="projet" peutEditer={peut('editer_projet_attestation')} />
      )}
      {etape === 'definitive' && <AttestationStep demande={demande} kind="definitive" peutEditer={false} />}
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
        <p>
          Le brouillon {demande.reference}, son FDR et ses pièces seront supprimés. Cette action est
          irréversible.
        </p>
      </Modal>
    </>
  );
}

function VueSiege({ demande }: { demande: DemandeDetail }) {
  const [params, setParams] = useSearchParams();
  const vue = params.get('vue');
  // Un projet soumis attend le siège : on l'ouvre en priorité.
  const ongletParDefaut = demande.etat_attestation === 'PROJET_SOUMIS' ? 'projet' : 'dossier';
  const onglet = params.get('onglet') ?? (vue && VUE_VERS_ONGLET[vue]) ?? ongletParDefaut;
  const onglets = [
    { cle: 'dossier', libelle: 'Dossier (FDR)' },
    { cle: 'pieces', libelle: 'Risque & pièces' },
    { cle: 'projet', libelle: "Projet d'attestation" },
    ...(demande.decision === 'ACCEPTEE' ? [{ cle: 'definitive', libelle: 'Attestation définitive' }] : []),
    { cle: 'historique', libelle: 'Historique' },
  ];
  return (
    <>
      <EnTete demande={demande} />
      {demande.etat_attestation === 'PROJET_SOUMIS' && (
        <Alert type="warning">
          <strong>Projet d'attestation soumis par le distributeur :</strong> à valider ou à rectifier pour
          établir l'attestation définitive (onglet « Projet d'attestation »).
        </Alert>
      )}
      <div className="grid-2 mb-2" style={{ gridTemplateColumns: 'minmax(0, 2fr) minmax(300px, 1fr)' }}>
        <TraitementPanel demande={demande} />
        <Card titre="Synthèse" variante="plain">
          <div className="recap">
            <dl>
              <dt>Distributeur</dt>
              <dd>
                {demande.distributeur.nom_affichage}
                <div className="small muted">{demande.distributeur.organisation}</div>
              </dd>
              <dt>Envoyée le</dt>
              <dd>
                {formatDateHeure(demande.submitted_at)} (n°{demande.nb_soumissions})
              </dd>
              <dt>Relances</dt>
              <dd>
                {demande.nb_relances}
                {demande.derniere_relance_le && (
                  <span className="small muted">
                    {' '}
                    · dernière le {formatDateHeure(demande.derniere_relance_le)}
                  </span>
                )}
              </dd>
              <dt>Commentaire distributeur</dt>
              <dd>{demande.commentaire_distributeur || '—'}</dd>
            </dl>
          </div>
          {demande.scoring_snapshot && (
            <div className="mt-2">
              <BadgeNiveau niveau={demande.scoring_snapshot.niveau} />{' '}
              <strong>{demande.scoring_snapshot.score}/100</strong>
              <p className="small mt-1">{demande.scoring_snapshot.synthese}</p>
            </div>
          )}
        </Card>
      </div>
      <Tabs onglets={onglets} actif={onglet} onChange={(o) => setParams({ onglet: o })} />
      {onglet === 'dossier' && <FdrForm demande={demande} lectureSeule />}
      {onglet === 'pieces' && <RisquePiecesStep demande={demande} lectureSeule />}
      {onglet === 'projet' && (
        <AttestationStep
          demande={demande}
          kind="projet"
          peutEditer={false}
          onEtablirDefinitive={() => setParams({ onglet: 'definitive' })}
        />
      )}
      {onglet === 'definitive' && (
        <AttestationStep
          demande={demande}
          kind="definitive"
          peutEditer={demande.actions_possibles.includes('editer_attestation_definitive')}
        />
      )}
      {onglet === 'historique' && <HistoriquePanel demande={demande} />}
    </>
  );
}

function HistoriquePanel({ demande }: { demande: DemandeDetail }) {
  const { data: historique } = useHistorique(demande.id);
  const { data: soumissions } = useSoumissions(demande.id);
  const toast = useToast();
  return (
    <div className="grid-2">
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
      <Card titre="📑 Soumissions au siège (FDR PDF)">
        {!soumissions ? (
          <Spinner />
        ) : soumissions.length === 0 ? (
          <p className="muted">Aucun envoi pour le moment.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>N°</th>
                <th>Date</th>
                <th>Risque</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {soumissions.map((s) => (
                <tr key={s.id}>
                  <td>{s.numero}</td>
                  <td>{formatDateHeure(s.created_at)}</td>
                  <td>
                    <BadgeNiveau niveau={s.scoring_snapshot.niveau} />
                  </td>
                  <td>
                    <Button
                      variante="secondary"
                      taille="sm"
                      onClick={() =>
                        telechargerFichier(
                          `/demandes/${demande.id}/soumissions/${s.numero}/pdf/`,
                          `FDR-${demande.reference}-${s.numero}.pdf`,
                        ).catch((e) => toast.erreur(e))
                      }
                    >
                      📄 FDR PDF
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
