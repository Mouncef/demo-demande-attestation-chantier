import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import type { Role } from '@/api/types';
import { useAuth } from '@/features/auth/AuthContext';
import { Spinner } from '@/design-system/components';

/** Garde de route : redirige vers /login si non connecté, vers l'accueil si le rôle ne convient pas. */
export function RequireAuth({ children, role }: { children: ReactNode; role?: Role }) {
  const { utilisateur, chargement } = useAuth();
  const location = useLocation();
  if (chargement) return <Spinner label="Vérification de la session…" />;
  if (!utilisateur) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (role && utilisateur.role !== role) return <Navigate to="/" replace />;
  return <>{children}</>;
}
