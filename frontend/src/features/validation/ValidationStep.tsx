// Écran 4 : récapitulatif, commentaire, vérification de complétude, sauvegarde et envoi au siège.
import { useState } from 'react';
import { useActionDemande, useCommentaire, useCompletude, useReferentiels } from '@/api/demandes';
import type { DemandeDetail } from '@/api/types';
import { formatDate, formatMontant } from '@/lib/format';
import { LIBELLES_INTERVENTION, LIBELLES_TYPE_CHANTIER, LIBELLES_USAGE } from '@/lib/libelles';
import { Alert, Button, Card, Modal, Textarea, useToast } from '@/design-system/components';

const ouiNon = (v: boolean | null) => (v === null ? '—' : v ? 'Oui' : 'Non');

export function ValidationStep({
  demande,
  lectureSeule,
  onEnvoye,
  onAllerEtape,
}: {
  demande: DemandeDetail;
  lectureSeule: boolean;
  onEnvoye: () => void;
  onAllerEtape: (cle: string) => void;
}) {
  const { data: completude } = useCompletude(demande.id);
  const { data: referentiels } = useReferentiels();
  const [commentaire, setCommentaire] = useState(demande.commentaire_distributeur);
  const [confirmer, setConfirmer] = useState(false);
  const sauver = useCommentaire(demande.id);
  const envoyer = useActionDemande(demande.id, 'envoyer');
  const toast = useToast();
  const f = demande.fdr;
  const e = completude?.erreurs_fdr ?? {};
  const libellesPieces = Object.fromEntries(
    (referentiels?.types_pieces ?? []).map((t) => [t.code, t.libelle]),
  );
  const pret = Boolean(completude?.pret_pour_envoi);

  const ligne = (cle: keyof typeof f, libelle: string, valeur: string) => (
    <>
      <dt>{libelle}</dt>
      <dd className={e[cle] ? 'invalid' : ''}>
        {valeur}
        {e[cle] && <span className="small"> — {e[cle]}</span>}
      </dd>
    </>
  );

  const confirmerEnvoi = async () => {
    try {
      await envoyer.mutateAsync({ commentaire });
      toast.notifier('Demande envoyée au siège. Le PDF du FDR a été généré.', 'success');
      setConfirmer(false);
      onEnvoye();
    } catch (err) {
      toast.erreur(err);
      setConfirmer(false);
    }
  };

  return (
    <>
      {completude && !pret && (
        <Alert type="danger">
          <strong>Envoi impossible : le dossier n'est pas prêt.</strong>
          <ul>
            {!completude.fdr_valide && (
              <li>
                Le FDR est incomplet ou invalide ({Object.keys(e).length} champ(s)) —{' '}
                <button type="button" className="btn btn--ghost btn--sm" onClick={() => onAllerEtape('fdr')}>
                  corriger le FDR
                </button>
              </li>
            )}
            {completude.manquants.map((m) => (
              <li key={m}>
                Pièce manquante : <strong>{libellesPieces[m] ?? m}</strong>
              </li>
            ))}
            {completude.manquants.length > 0 && (
              <li>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => onAllerEtape('pieces')}
                >
                  déposer les pièces
                </button>
              </li>
            )}
          </ul>
        </Alert>
      )}
      {completude && pret && !lectureSeule && (
        <Alert type="success">
          <strong>Dossier complet et FDR valide</strong> : la demande peut être envoyée au siège.
        </Alert>
      )}

      <div className="grid-2">
        <Card titre="Récapitulatif – assuré et chantier" className="recap">
          <dl>
            {ligne('assure_nom', 'Assuré', f.assure_nom ?? '—')}
            {ligne(
              'assure_adresse',
              'Adresse',
              `${f.assure_adresse ?? '—'}${f.assure_code_postal || f.assure_ville ? ` – ${f.assure_code_postal ?? ''} ${f.assure_ville ?? ''}` : ''}`,
            )}
            {ligne('assure_siret', 'SIRET', f.assure_siret ?? '—')}
            {ligne(
              'numero_contrat',
              'Contrat',
              `${f.numero_contrat ?? '—'}${f.reference_client ? ` (réf. client ${f.reference_client})` : ''}`,
            )}
            {ligne('chantier_nom', 'Chantier', f.chantier_nom ?? '—')}
            {ligne('chantier_ville', 'Ville du chantier', f.chantier_ville ?? '—')}
            {ligne('type_chantier', 'Type', f.type_chantier ? LIBELLES_TYPE_CHANTIER[f.type_chantier] : '—')}
            {f.type_chantier === 'RENOVATION' &&
              ligne('modification_structure', 'Modification structure', ouiNon(f.modification_structure))}
            {ligne(
              'usage',
              'Usage',
              f.usage
                ? `${LIBELLES_USAGE[f.usage]}${f.usage_autre_precision ? ` : ${f.usage_autre_precision}` : ''}`
                : '—',
            )}
            {ligne('chantier_atypique', 'Chantier atypique', ouiNon(f.chantier_atypique))}
            {ligne('date_debut', 'Période', `${formatDate(f.date_debut)} → ${formatDate(f.date_fin)}`)}
            {ligne('cout_total', 'Coût total', formatMontant(f.cout_total))}
          </dl>
        </Card>
        <Card titre="Récapitulatif – intervention" className="recap">
          <dl>
            {ligne('description_travaux', 'Travaux', f.description_travaux ?? '—')}
            {ligne('montant_prestation', 'Montant prestation', formatMontant(f.montant_prestation))}
            {ligne(
              'type_intervention',
              'Intervention',
              f.type_intervention ? LIBELLES_INTERVENTION[f.type_intervention] : '—',
            )}
            {f.entreprise_principale_nom &&
              ligne('entreprise_principale_nom', 'Entreprise principale', f.entreprise_principale_nom)}
            {ligne('activite_couverte', 'Activité couverte', ouiNon(f.activite_couverte))}
            {f.activite_couverte === false &&
              ligne(
                'activite_non_couverte_precision',
                'Activité non couverte',
                f.activite_non_couverte_precision ?? '—',
              )}
            {ligne('travaux_standards', 'Travaux standards', ouiNon(f.travaux_standards))}
          </dl>
          {completude && (
            <div className="mt-2">
              <strong>Pièces :</strong>{' '}
              {completude.exigences.length === 0
                ? 'aucune pièce requise'
                : `${completude.exigences.filter((x) => x.satisfait).length}/${completude.exigences.length} fournie(s)`}
              {completude.pieces_hors_exigence.length > 0 &&
                ` · ${completude.pieces_hors_exigence.length} facultative(s)`}
            </div>
          )}
        </Card>
      </div>

      <Card titre="💬 Commentaire pour le siège" className="mt-2">
        <Textarea
          value={commentaire}
          onChange={(ev) => setCommentaire(ev.target.value)}
          disabled={lectureSeule}
          maxLength={2000}
          placeholder="Contexte, urgence, précisions utiles à l'instruction…"
        />
        {!lectureSeule && (
          <div className="actions mt-2">
            <Button
              variante="secondary"
              chargement={sauver.isPending}
              onClick={() =>
                sauver.mutate(commentaire, {
                  onSuccess: () => toast.notifier('Commentaire sauvegardé.', 'success'),
                  onError: (err) => toast.erreur(err),
                })
              }
            >
              💾 Sauvegarder
            </Button>
            <Button
              disabled={!pret}
              onClick={() => setConfirmer(true)}
              title={pret ? undefined : 'Complétez le dossier avant envoi'}
            >
              🚀 Envoyer au siège
            </Button>
          </div>
        )}
      </Card>

      <Modal
        ouvert={confirmer}
        titre="Confirmer l'envoi au siège"
        onFermer={() => setConfirmer(false)}
        pied={
          <>
            <Button variante="secondary" onClick={() => setConfirmer(false)}>
              Annuler
            </Button>
            <Button onClick={confirmerEnvoi} chargement={envoyer.isPending}>
              Confirmer l'envoi
            </Button>
          </>
        }
      >
        <p>
          Une fois envoyée, la demande passe au statut <strong>En cours</strong> : le FDR et les pièces ne
          seront plus modifiables (sauf si le siège demande des compléments).
        </p>
        <p>Le PDF du FDR sera généré et le siège sera notifié par email.</p>
      </Modal>
    </>
  );
}
