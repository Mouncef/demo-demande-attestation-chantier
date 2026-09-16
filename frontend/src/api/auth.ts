import { api, tokens } from './client';
import type { LoginReponse, Utilisateur } from './types';

export async function login(email: string, password: string): Promise<LoginReponse> {
  const { data } = await api.post<LoginReponse>('/auth/login/', { email, password });
  tokens.set(data.access, data.refresh);
  return data;
}

export async function logout(): Promise<void> {
  const refresh = tokens.refresh;
  try {
    if (refresh) await api.post('/auth/logout/', { refresh });
  } finally {
    tokens.clear();
  }
}

export async function me(): Promise<Utilisateur> {
  const { data } = await api.get<Utilisateur>('/auth/me/');
  return data;
}
