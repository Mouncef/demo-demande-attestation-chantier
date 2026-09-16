// Hooks React Query pour les demandes, le FDR, la complétude, le scoring et les référentiels.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './client';
import type {
  Completude,
  DemandeDetail,
  DemandeListe,
  FDR,
  Historique,
  Pagination,
  Referentiels,
  Scoring,
} from './types';

export const cles = {
  demandes: (params?: FiltresDemandes) => ['demandes', params ?? {}] as const,
  demande: (id: string) => ['demande', id] as const,
  completude: (id: string) => ['demande', id, 'completude'] as const,
  scoring: (id: string) => ['demande', id, 'scoring'] as const,
  historique: (id: string) => ['demande', id, 'historique'] as const,
  referentiels: ['referentiels'] as const,
};

export interface FiltresDemandes {
  statut?: string[];
  decision?: string[];
  search?: string;
  ordering?: string;
  page?: number;
  /** Nombre de lignes par page (bornée à 100 par l'API). */
  pageSize?: number;
}

export function useDemandes(filtres: FiltresDemandes) {
  return useQuery({
    queryKey: cles.demandes(filtres),
    queryFn: async () => {
      const params = new URLSearchParams();
      filtres.statut?.forEach((s) => params.append('statut', s));
      filtres.decision?.forEach((d) => params.append('decision', d));
      if (filtres.search) params.set('search', filtres.search);
      if (filtres.ordering) params.set('ordering', filtres.ordering);
      if (filtres.page) params.set('page', String(filtres.page));
      if (filtres.pageSize) params.set('page_size', String(filtres.pageSize));
      const { data } = await api.get<Pagination<DemandeListe>>('/demandes/', { params });
      return data;
    },
  });
}

export function useDemande(id: string | undefined) {
  return useQuery({
    queryKey: cles.demande(id ?? ''),
    queryFn: async () => (await api.get<DemandeDetail>(`/demandes/${id}/`)).data,
    enabled: Boolean(id),
  });
}

export function useCompletude(id: string, enabled = true) {
  return useQuery({
    queryKey: cles.completude(id),
    queryFn: async () => (await api.get<Completude>(`/demandes/${id}/completude/`)).data,
    enabled,
  });
}

export function useScoring(id: string, enabled = true) {
  return useQuery({
    queryKey: cles.scoring(id),
    queryFn: async () => (await api.get<Scoring>(`/demandes/${id}/scoring/`)).data,
    enabled,
  });
}

export function useHistorique(id: string) {
  return useQuery({
    queryKey: cles.historique(id),
    queryFn: async () => (await api.get<Historique[]>(`/demandes/${id}/historique/`)).data,
  });
}

export function useReferentiels() {
  return useQuery({
    queryKey: cles.referentiels,
    queryFn: async () => (await api.get<Referentiels>('/referentiels/')).data,
    staleTime: Infinity,
  });
}

/** Invalide toutes les données dérivées d'une demande après une action. */
export function useInvaliderDemande() {
  const qc = useQueryClient();
  return (id: string) => {
    void qc.invalidateQueries({ queryKey: ['demande', id] });
    void qc.invalidateQueries({ queryKey: ['demandes'] });
  };
}

export function useCreerDemande() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => (await api.post<DemandeDetail>('/demandes/')).data,
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['demandes'] }),
  });
}

export function useSupprimerDemande() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => api.delete(`/demandes/${id}/`),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['demandes'] }),
  });
}

export function useEnregistrerFdr(id: string) {
  const invalider = useInvaliderDemande();
  return useMutation({
    mutationFn: async (payload: Partial<FDR> & { version: number }) =>
      (await api.patch<DemandeDetail>(`/demandes/${id}/fdr/`, payload)).data,
    onSuccess: () => invalider(id),
  });
}
