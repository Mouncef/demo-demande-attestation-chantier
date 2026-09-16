import { useState, type FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { erreurApi } from '@/api/client';
import { Alert, Button, Field, Input } from '@/design-system/components';
import { useAuth } from './AuthContext';

const COMPTES_DEMO = [
  { email: 'distributeur@axa-demo.fr', libelle: 'Distributeur (agent général)' },
  { email: 'distributeur2@axa-demo.fr', libelle: 'Distributeur (courtier)' },
  { email: 'siege@axa-demo.fr', libelle: 'Siège' },
];

export function LoginPage() {
  const { utilisateur, connecter } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [erreur, setErreur] = useState<string | null>(null);
  const [chargement, setChargement] = useState(false);

  if (utilisateur) return <Navigate to="/demandes" replace />;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErreur(null);
    setChargement(true);
    try {
      await connecter(email.trim(), password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && from !== '/login' ? from : '/demandes', { replace: true });
    } catch (err) {
      const e = erreurApi(err);
      setErreur(
        e.code === 'TROP_DE_REQUETES'
          ? 'Trop de tentatives, réessayez dans quelques instants.'
          : e.code === 'RESEAU'
            ? e.detail
            : 'Identifiants incorrects ou compte désactivé.',
      );
    } finally {
      setChargement(false);
    }
  };

  return (
    <div className="login">
      <aside className="login__brand">
        {/* Hero Switch : diagonale rouge centrée sur la composition (≥ 50 % de hauteur, trois coins visibles). */}
        <svg
          className="login__switch"
          viewBox="0 0 100 100"
          preserveAspectRatio="xMidYMid slice"
          aria-hidden
          focusable="false"
        >
          <path d="M58 20h6L42 80h-6z" fill="#ff1721" />
        </svg>
        <img
          src="/logo.png"
          alt="AXA"
          style={{ width: 88, height: 88, position: 'relative', zIndex: 1, background: '#fff' }}
        />
        <h1 className="mt-3">Attestations de chantier</h1>
        <p style={{ fontSize: '1.1rem', maxWidth: 420 }}>
          Déclarez le risque, joignez vos pièces, suivez l'instruction par le siège et obtenez votre
          attestation.
        </p>
      </aside>
      <div className="login__form">
        <form className="card login__card" onSubmit={onSubmit} noValidate>
          <h2>Connexion</h2>
          {erreur && <Alert type="danger">{erreur}</Alert>}
          <Field label="Adresse email" requis>
            {(id) => (
              <Input
                id={id}
                type="email"
                autoComplete="username"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            )}
          </Field>
          <Field label="Mot de passe" requis>
            {(id) => (
              <Input
                id={id}
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            )}
          </Field>
          <Button type="submit" chargement={chargement} style={{ width: '100%' }} taille="lg">
            Se connecter
          </Button>
          <div className="demo-accounts mt-2">
            <strong>Comptes de démonstration</strong> (mot de passe indiqué dans le README) :
            <ul style={{ margin: '0.25rem 0 0', paddingLeft: '1.1rem' }}>
              {COMPTES_DEMO.map((c) => (
                <li key={c.email}>
                  <button type="button" onClick={() => setEmail(c.email)}>
                    {c.email}
                  </button>{' '}
                  – {c.libelle}
                </li>
              ))}
            </ul>
          </div>
        </form>
      </div>
    </div>
  );
}
