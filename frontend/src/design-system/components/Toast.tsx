/* eslint-disable react-refresh/only-export-components -- provider + hook volontairement colocalisés */
// Système de notifications éphémères (toasts) via contexte React.
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { erreurApi } from '@/api/client';
import { LIBELLES_ERREURS_API } from '@/lib/libelles';

type Type = 'info' | 'success' | 'error';
interface Toast {
  id: number;
  type: Type;
  message: string;
}
interface Ctx {
  notifier: (message: string, type?: Type) => void;
  /** Affiche une erreur API traduite (message métier si connu, sinon le `detail` renvoyé). */
  erreur: (error: unknown, fallback?: string) => void;
}

const ToastContext = createContext<Ctx | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const notifier = useCallback((message: string, type: Type = 'info') => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, type, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), type === 'error' ? 7000 : 4000);
  }, []);
  const erreur = useCallback(
    (error: unknown, fallback?: string) => {
      const e = erreurApi(error);
      const message =
        e.code === 'VALIDATION' && e.errors
          ? `${LIBELLES_ERREURS_API.VALIDATION} ${Object.values(e.errors).flat().join(' ')}`
          : (LIBELLES_ERREURS_API[e.code] ?? e.detail ?? fallback ?? 'Une erreur est survenue.');
      notifier(message, 'error');
    },
    [notifier],
  );
  const valeur = useMemo(() => ({ notifier, erreur }), [notifier, erreur]);
  return (
    <ToastContext.Provider value={valeur}>
      {children}
      <div className="toasts" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast--${t.type}`} role="status">
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): Ctx {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast doit être utilisé dans <ToastProvider>');
  return ctx;
}
