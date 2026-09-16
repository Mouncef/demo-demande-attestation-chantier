// Cloche de notifications : compteur (polling 30 s) et panneau déroulant des dernières notifications.
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCompteurNotifications, useMarquerLue, useNotifications, useToutMarquerLu } from '@/api/notifications';
import type { Notification } from '@/api/types';
import { formatDateHeure } from '@/lib/format';
import { Button } from '@/design-system/components';

export function NotificationsBell() {
  const [ouvert, setOuvert] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { data: count = 0 } = useCompteurNotifications();
  const { data } = useNotifications(false);
  const marquer = useMarquerLue();
  const toutLu = useToutMarquerLu();

  useEffect(() => {
    if (!ouvert) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOuvert(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [ouvert]);

  const ouvrir = (n: Notification) => {
    if (!n.lu) marquer.mutate(n.id);
    setOuvert(false);
    if (n.payload.demande_id) navigate(`/demandes/${n.payload.demande_id}${n.payload.onglet ? `?vue=${n.payload.onglet}` : ''}`);
  };

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        type="button"
        className="bell"
        aria-label={`Notifications${count ? ` (${count} non lues)` : ''}`}
        aria-expanded={ouvert}
        onClick={() => setOuvert((o) => !o)}
      >
        🔔
        {count > 0 && <span className="bell__count">{count > 99 ? '99+' : count}</span>}
      </button>
      {ouvert && (
        <div className="bell-panel">
          <div className="flex between" style={{ padding: '0.6rem 1rem', borderBottom: '1px solid var(--axa-gray-200)' }}>
            <strong>Notifications</strong>
            <Button variante="ghost" taille="sm" onClick={() => toutLu.mutate()} disabled={!count}>
              Tout marquer lu
            </Button>
          </div>
          {data?.results.length ? (
            data.results.slice(0, 8).map((n) => (
              <div key={n.id} className={`notif ${n.lu ? '' : 'notif--non-lue'}`} onClick={() => ouvrir(n)} role="button" tabIndex={0}>
                <div className="notif__titre">{n.titre}</div>
                <div className="small">{n.message}</div>
                <div className="notif__date">{formatDateHeure(n.created_at)}</div>
              </div>
            ))
          ) : (
            <div className="empty">Aucune notification</div>
          )}
          <div style={{ padding: '0.5rem 1rem', textAlign: 'center' }}>
            <Button variante="ghost" taille="sm" onClick={() => { setOuvert(false); navigate('/notifications'); }}>
              Voir toutes les notifications
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
