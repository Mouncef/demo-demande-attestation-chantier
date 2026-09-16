import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './client';
import type { PieceJointe } from './types';

export function usePieces(demandeId: string) {
  return useQuery({
    queryKey: ['demande', demandeId, 'pieces'],
    queryFn: async () => (await api.get<PieceJointe[]>(`/demandes/${demandeId}/pieces/`)).data,
  });
}

function useInvaliderPieces(demandeId: string) {
  const qc = useQueryClient();
  return () => void qc.invalidateQueries({ queryKey: ['demande', demandeId] });
}

export function useUploaderPiece(demandeId: string) {
  const invalider = useInvaliderPieces(demandeId);
  return useMutation({
    mutationFn: async ({ fichier, typePiece }: { fichier: File; typePiece: string }) => {
      const form = new FormData();
      form.append('fichier', fichier);
      form.append('type_piece', typePiece);
      return (await api.post<PieceJointe>(`/demandes/${demandeId}/pieces/`, form)).data;
    },
    onSuccess: invalider,
  });
}

export function useSupprimerPiece(demandeId: string) {
  const invalider = useInvaliderPieces(demandeId);
  return useMutation({
    mutationFn: async (pieceId: string) => api.delete(`/demandes/${demandeId}/pieces/${pieceId}/`),
    onSuccess: invalider,
  });
}

export function useChangerTypePiece(demandeId: string) {
  const invalider = useInvaliderPieces(demandeId);
  return useMutation({
    mutationFn: async ({ pieceId, typePiece }: { pieceId: string; typePiece: string }) =>
      (await api.patch<PieceJointe>(`/demandes/${demandeId}/pieces/${pieceId}/`, { type_piece: typePiece })).data,
    onSuccess: invalider,
  });
}
