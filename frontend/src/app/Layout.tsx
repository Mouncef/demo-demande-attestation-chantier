// Gabarit de page : en-tête AXA (logo, diagonale rouge), navigation, cloche de notifications.
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '@/features/auth/AuthContext';
import { NotificationsBell } from '@/features/notifications/NotificationsBell';
import { Button } from '@/design-system/components';

export function Layout() {
  const { utilisateur, deconnecter } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="layout">
      <header className="header">
        <div className="header__inner">
          <NavLink to="/demandes" className="brand" aria-label="Accueil">
            <img className="brand__logo" src="/logo.png" alt="AXA" />
            <span className="brand__title">Attestations de chantier</span>
          </NavLink>
          <nav className="nav" aria-label="Navigation principale">
            <NavLink to="/demandes">Demandes</NavLink>
            <NavLink to="/reporting">Reporting</NavLink>
          </nav>
          {/* Mini Switch : signature AXA issue du logo, une seule fois par écran. */}
          <svg className="header__switch" viewBox="0 0 22 44" aria-hidden focusable="false">
            <path d="M16 0h6L6 44H0z" fill="#ff1721" />
          </svg>
          <div className="header__right">
            <NotificationsBell />
            <div className="user">
              <span className="user__name">{utilisateur?.nom_affichage}</span>
              <span className="user__role">{utilisateur?.role === 'SIEGE' ? 'Siège' : 'Distributeur'}</span>
            </div>
            <Button
              variante="ghost"
              taille="sm"
              className="btn--on-dark"
              onClick={async () => {
                await deconnecter();
                navigate('/login');
              }}
            >
              Déconnexion
            </Button>
          </div>
        </div>
      </header>
      <main className="main">
        <Outlet />
      </main>
      <footer className="footer">
        Plateforme interne de gestion des demandes d'attestation de chantier – test technique AXA ·
        démonstration
      </footer>
    </div>
  );
}
