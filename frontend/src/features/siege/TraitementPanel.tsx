// Écran 5 : traitement par le siège – consultation, commentaire, accepter / refuser (motivé) /
// demander des éléments complémentaires.
import { useState } from 'react';
import { useActionDemande, useCommentaire } from '@/api/demandes';
import type { DemandeDetail } from '@/api/types';
import { Alert, Button, Card, Modal, Textarea, useToast } from '@/design-system/components';

type Action = 'accepter' | 'refuser' | 'demander_complements' | null;

export function TraitementPanel({ demande }: { demande: DemandeDetail }) {
  const toast = useToast();
  const [commentaire, setCommentaire] = useState(demande.commentaire_siege);
  const [action, setAction] = useState<Action>(null);
  const [motif, setMotif] = useState('');
  const sauver = useCommentaire(demande.id);
  const accepter = useActionDemande(demande.id, 'accepter');
  const refuser = useActionDemande(demande.id, 'refuser');
  const complements = useActionDemande(demande.id, 'demander-complements');
  const peut = (a: string) => demande.actions_possibles.includes(a as never);
  const enCours = accepter.isPending || refuser.isPending || complements.isPending;

  const executer = async () => {
    try {
      if (action === 'accepter') {
        await accepter.mutateAsync({ commentaire });
        toast.notifier(
          'Demande acceptée : le distributeur est notifié et prépare son projet d’attestation.',
          'success',
        );
      } else if (action === 'refuser') {
        await refuser.mutateAsync({ motif, commentaire });
        toast.notifier('Demande refusée, le distributeur est notifié.', 'success');
      } else if (action === 'demander_complements') {
        await complements.mutateAsync({ message: motif });
        toast.notifier('Compléments demandés, le distributeur est notifié.', 'success');
      }
      setAction(null);
      setMotif('');
    } catch (e) {
      toast.erreur(e);
    }
  };

  const titres: Record<NonNullable<Action>, string> = {
    accepter: 'Accepter la demande',
    refuser: 'Refuser la demande',
    demander_complements: 'Demander des éléments complémentaires',
  };

  return (
    <Card titre="🏢 Instruction par le siège" variante="plain">
      {demande.statut === 'A_COMPLETER' && (
        <Alert type="warning">
          Compléments demandés au distributeur : <em>{demande.message_complements}</em>. En attente de renvoi.
        </Alert>
      )}
      {demande.statut === 'TRAITE' && (
        <Alert type={demande.decision === 'ACCEPTEE' ? 'success' : 'danger'}>
          Demande <strong>{demande.decision === 'ACCEPTEE' ? 'acceptée' : 'refusée'}</strong> par{' '}
          {demande.decided_by?.nom_affichage}.
          {demande.motif_refus && <div>Motif : {demande.motif_refus}</div>}
        </Alert>
      )}
      <label className="field__label" htmlFor="commentaire-siege">
        Commentaire interne du siège
      </label>
      <Textarea
        id="commentaire-siege"
        value={commentaire}
        onChange={(e) => setCommentaire(e.target.value)}
        disabled={!peut('commenter')}
        maxLength={2000}
      />
      <div className="actions mt-2">
        {peut('commenter') && (
          <Button
            variante="secondary"
            chargement={sauver.isPending}
            onClick={() =>
              sauver.mutate(commentaire, {
                onSuccess: () => toast.notifier('Commentaire sauvegardé.', 'success'),
                onError: (e) => toast.erreur(e),
              })
            }
          >
            💾 Sauvegarder le commentaire
          </Button>
        )}
        <span className="right" />
        {peut('demander_complements') && (
          <Button variante="secondary" onClick={() => setAction('demander_complements')}>
            📎 Demander des compléments
          </Button>
        )}
        {peut('refuser') && (
          <Button variante="danger" onClick={() => setAction('refuser')}>
            ❌ Refuser
          </Button>
        )}
        {peut('accepter') && (
          <Button variante="success" onClick={() => setAction('accepter')}>
            ✅ Accepter
          </Button>
        )}
      </div>

      <Modal
        ouvert={action !== null}
        titre={action ? titres[action] : ''}
        onFermer={() => setAction(null)}
        pied={
          <>
            <Button variante="secondary" onClick={() => setAction(null)}>
              Annuler
            </Button>
            <Button
              variante={action === 'refuser' ? 'danger' : action === 'accepter' ? 'success' : 'primary'}
              chargement={enCours}
              disabled={action !== 'accepter' && motif.trim().length < 10}
              onClick={executer}
            >
              Confirmer
            </Button>
          </>
        }
      >
        {action === 'accepter' && (
          <p>
            La demande passera au statut <strong>Traitée – Acceptée</strong>. Le distributeur sera notifié et
            préparera son projet d'attestation, à partir duquel vous établirez l'attestation définitive.
          </p>
        )}
        {action === 'refuser' && (
          <>
            <p>Le refus doit être motivé (10 caractères minimum). Le motif sera transmis au distributeur.</p>
            <Textarea
              value={motif}
              onChange={(e) => setMotif(e.target.value)}
              placeholder="Motif du refus…"
              autoFocus
            />
          </>
        )}
        {action === 'demander_complements' && (
          <>
            <p>
              Décrivez les éléments attendus : le distributeur pourra modifier le FDR et ajouter des pièces,
              puis renvoyer la demande.
            </p>
            <Textarea
              value={motif}
              onChange={(e) => setMotif(e.target.value)}
              placeholder="Éléments complémentaires attendus…"
              autoFocus
            />
          </>
        )}
      </Modal>
    </Card>
  );
}
