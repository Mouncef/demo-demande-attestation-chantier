import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './client';
import type { Notification, Pagination } from './types';

export function useNotifications(nonLues = false) {
  return useQuery({
    queryKey: ['notifications', 'liste', nonLues],
    queryFn: async () =>
      (await api.get<Pagination<Notification>>('/notifications/', { params: nonLues ? { lu: false } : {} })).data,
  });
}

/** Compteur de non-lues, rafraîchi toutes les 30 s (polling léger). */
export function useCompteurNotifications() {
  return useQuery({
    queryKey: ['notifications', 'count'],
    queryFn: async () => (await api.get<{ count: number }>('/notifications/non-lues/count/')).data.count,
    refetchInterval: 30_000,
  });
}

export function useMarquerLue() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => api.post(`/notifications/${id}/lire/`),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['notifications'] }),
  });
}

export function useToutMarquerLu() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => api.post('/notifications/lire-toutes/'),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ['notifications'] }),
  });
}
