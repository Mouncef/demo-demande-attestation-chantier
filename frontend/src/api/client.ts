// Client HTTP : injection du JWT, renouvellement automatique de l'access token,
// normalisation des erreurs. Les tokens sont conservés en mémoire + sessionStorage
// (fermeture de l'onglet = déconnexion), jamais en cookie (pas de CSRF).
import axios, { AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios';
import type { ErreurApi } from './types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';
const CLE_ACCESS = 'axa.access';
const CLE_REFRESH = 'axa.refresh';

export const tokens = {
  get access(): string | null {
    return sessionStorage.getItem(CLE_ACCESS);
  },
  get refresh(): string | null {
    return sessionStorage.getItem(CLE_REFRESH);
  },
  set(access: string, refresh: string) {
    sessionStorage.setItem(CLE_ACCESS, access);
    sessionStorage.setItem(CLE_REFRESH, refresh);
  },
  clear() {
    sessionStorage.removeItem(CLE_ACCESS);
    sessionStorage.removeItem(CLE_REFRESH);
  },
};

export const api = axios.create({ baseURL: BASE_URL, timeout: 30_000 });

/** Callback appelé lorsque la session ne peut plus être renouvelée (→ retour au login). */
let surDeconnexion: (() => void) | null = null;
export function setSurDeconnexion(cb: () => void) {
  surDeconnexion = cb;
}

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const access = tokens.access;
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

let renouvellementEnCours: Promise<string> | null = null;

/** Demande un nouvel access token (une seule requête de refresh à la fois). */
async function renouveler(): Promise<string> {
  if (!renouvellementEnCours) {
    const refresh = tokens.refresh;
    if (!refresh) throw new Error('Pas de refresh token');
    renouvellementEnCours = axios
      .post<{ access: string; refresh?: string }>(`${BASE_URL}/auth/refresh/`, { refresh })
      .then(({ data }) => {
        tokens.set(data.access, data.refresh ?? refresh);
        return data.access;
      })
      .finally(() => {
        renouvellementEnCours = null;
      });
  }
  return renouvellementEnCours;
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError<ErreurApi>) => {
    const config = error.config as (AxiosRequestConfig & { _retry?: boolean }) | undefined;
    const estAuth = config?.url?.includes('/auth/');
    if (error.response?.status === 401 && config && !config._retry && !estAuth && tokens.refresh) {
      config._retry = true;
      try {
        const access = await renouveler();
        config.headers = { ...config.headers, Authorization: `Bearer ${access}` };
        return api.request(config);
      } catch {
        tokens.clear();
        surDeconnexion?.();
      }
    }
    return Promise.reject(error);
  },
);

/** Extrait l'erreur normalisée `{code, detail, errors}` d'une erreur axios. */
export function erreurApi(error: unknown): ErreurApi {
  if (axios.isAxiosError<ErreurApi>(error)) {
    if (error.response?.data && typeof error.response.data === 'object' && 'code' in error.response.data) {
      return error.response.data;
    }
    if (error.response) return { code: `HTTP_${error.response.status}`, detail: error.message };
    return { code: 'RESEAU', detail: 'Le serveur est injoignable. Vérifiez votre connexion.' };
  }
  return { code: 'INCONNUE', detail: error instanceof Error ? error.message : 'Erreur inattendue.' };
}

/** Télécharge un fichier binaire authentifié et déclenche l'enregistrement côté navigateur. */
export async function telechargerFichier(url: string, nomParDefaut: string): Promise<void> {
  const reponse = await api.get<Blob>(url, { responseType: 'blob' });
  const disposition = reponse.headers['content-disposition'] as string | undefined;
  const match = disposition?.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
  const nom = match ? decodeURIComponent(match[1]) : nomParDefaut;
  const lien = document.createElement('a');
  lien.href = URL.createObjectURL(reponse.data);
  lien.download = nom;
  document.body.appendChild(lien);
  lien.click();
  lien.remove();
  URL.revokeObjectURL(lien.href);
}
