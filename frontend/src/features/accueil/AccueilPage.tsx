// Page d'accueil provisoire : confirme la session et le rôle de l'utilisateur connecté.
import { Card } from '@/design-system/components';
import { useAuth } from '@/features/auth/AuthContext';

export function AccueilPage() {
  const { utilisateur } = useAuth();
  return (
    <div className="page">
      <h1>Bienvenue, {utilisateur?.nom_affichage}</h1>
      <Card titre="Espace de travail">
        <p>
          Vous êtes connecté en tant que <strong>{utilisateur?.role === 'SIEGE' ? 'siège' : 'distributeur'}</strong>
          {utilisateur?.organisation ? ` (${utilisateur.organisation})` : ''}. La gestion des demandes
          d'attestation sera disponible dans cet espace.
        </p>
      </Card>
    </div>
  );
}
