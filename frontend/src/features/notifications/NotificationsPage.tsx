import { useNavigate } from 'react-router-dom';
import { useMarquerLue, useNotifications, useToutMarquerLu } from '@/api/notifications';
import { formatDateHeure } from '@/lib/format';
import { Button, Card, EmptyState, Spinner } from '@/design-system/components';

export function NotificationsPage() {
  const { data, isLoading } = useNotifications(false);
  const marquer = useMarquerLue();
  const toutLu = useToutMarquerLu();
  const navigate = useNavigate();
  return (
    <>
      <div className="page-header">
        <h1>Notifications</h1>
        <Button variante="secondary" onClick={() => toutLu.mutate()}>
          Tout marquer comme lu
        </Button>
      </div>
      <Card>
        {isLoading && <Spinner />}
        {data && data.results.length === 0 && <EmptyState titre="Aucune notification" />}
        {data?.results.map((n) => (
          <div
            key={n.id}
            className={`notif ${n.lu ? '' : 'notif--non-lue'}`}
            role="button"
            tabIndex={0}
            onClick={() => {
              if (!n.lu) marquer.mutate(n.id);
              if (n.payload.demande_id) navigate(`/demandes/${n.payload.demande_id}`);
            }}
          >
            <div className="flex between">
              <span className="notif__titre">{n.titre}</span>
              <span className="notif__date">{formatDateHeure(n.created_at)}</span>
            </div>
            <div>{n.message}</div>
          </div>
        ))}
      </Card>
    </>
  );
}
