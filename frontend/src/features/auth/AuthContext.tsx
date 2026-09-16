/* eslint-disable react-refresh/only-export-components -- provider + hook volontairement colocalisés */
// Contexte d'authentification : utilisateur courant, connexion, déconnexion, expiration de session.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { setSurDeconnexion, tokens } from '@/api/client';
import * as authApi from '@/api/auth';
import type { Utilisateur } from '@/api/types';

interface Ctx {
  utilisateur: Utilisateur | null;
  chargement: boolean;
  connecter: (email: string, password: string) => Promise<Utilisateur>;
  deconnecter: () => Promise<void>;
}

const AuthContext = createContext<Ctx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [utilisateur, setUtilisateur] = useState<Utilisateur | null>(null);
  const [chargement, setChargement] = useState<boolean>(Boolean(tokens.access));
  const queryClient = useQueryClient();

  // Au chargement : si un token est présent, on recharge le profil (sinon on reste déconnecté).
  useEffect(() => {
    if (!tokens.access) return;
    authApi
      .me()
      .then(setUtilisateur)
      .catch(() => tokens.clear())
      .finally(() => setChargement(false));
  }, []);

  // Session non renouvelable (refresh expiré / révoqué) → déconnexion forcée.
  useEffect(() => {
    setSurDeconnexion(() => {
      setUtilisateur(null);
      queryClient.clear();
    });
  }, [queryClient]);

  const connecter = useCallback(async (email: string, password: string) => {
    const { utilisateur: u } = await authApi.login(email, password);
    setUtilisateur(u);
    return u;
  }, []);

  const deconnecter = useCallback(async () => {
    await authApi.logout();
    setUtilisateur(null);
    queryClient.clear();
  }, [queryClient]);

  const valeur = useMemo(() => ({ utilisateur, chargement, connecter, deconnecter }), [utilisateur, chargement, connecter, deconnecter]);
  return <AuthContext.Provider value={valeur}>{children}</AuthContext.Provider>;
}

export function useAuth(): Ctx {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth doit être utilisé dans <AuthProvider>');
  return ctx;
}
