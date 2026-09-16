// Bouton « Relancer le siège » : compte à rebours tant que le délai de 24 h n'est pas écoulé.
import { useEffect, useMemo, useState } from 'react';
import { useRelancer } from '@/api/demandes';
import { dureeRestante } from '@/lib/format';
import { Button, Modal, Textarea, useToast } from '@/design-system/components';

export function RelanceButton({
  demandeId,
  prochaine,
  taille = 'md',
}: {
  demandeId: string;
  prochaine: string | null;
  taille?: 'sm' | 'md';
}) {
  // `maintenant` est rafraîchi toutes les 30 s pour recalculer le délai restant (compte à rebours).
  const [maintenant, setMaintenant] = useState(() => Date.now());
  const [ouvert, setOuvert] = useState(false);
  const [message, setMessage] = useState('');
  const relancer = useRelancer(demandeId);
  const toast = useToast();

  useEffect(() => {
    const timer = setInterval(() => setMaintenant(Date.now()), 30_000);
    return () => clearInterval(timer);
  }, []);
  const restant = useMemo(() => dureeRestante(prochaine, maintenant), [prochaine, maintenant]);

  const envoyer = async () => {
    try {
      await relancer.mutateAsync(message);
      toast.notifier('Relance envoyée au siège par email.', 'success');
      setOuvert(false);
      setMessage('');
    } catch (e) {
      toast.erreur(e);
    }
  };

  return (
    <>
      <Button
        variante="secondary"
        taille={taille}
        disabled={Boolean(restant)}
        title={restant ? `Prochaine relance possible dans ${restant}` : 'Relancer le siège par email'}
        onClick={() => setOuvert(true)}
      >
        ✉ {restant ? `Relance dans ${restant}` : 'Relancer'}
      </Button>
      <Modal
        ouvert={ouvert}
        titre="Relancer le siège"
        onFermer={() => setOuvert(false)}
        pied={
          <>
            <Button variante="secondary" onClick={() => setOuvert(false)}>
              Annuler
            </Button>
            <Button onClick={envoyer} chargement={relancer.isPending}>
              Envoyer la relance
            </Button>
          </>
        }
      >
        <p>Un email de relance sera adressé au siège (une relance maximum par période de 24 h).</p>
        <Textarea
          placeholder="Message facultatif (contexte, urgence…)"
          maxLength={1000}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />
      </Modal>
    </>
  );
}
