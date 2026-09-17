import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { api } from './client';
import type { AnalyseIA, Attestation, Gabarit } from './types';

type Kind = 'projet' | 'definitive';
const base = (demandeId: string, kind: Kind) => `/demandes/${demandeId}/attestations/${kind}/`;

/** Attestation existante, ou `null` si elle n'a pas encore été créée (404 attendu). */
export function useAttestation(demandeId: string, kind: Kind) {
  return useQuery({
    queryKey: ['demande', demandeId, 'attestation', kind],
    queryFn: async () => {
      try {
        return (await api.get<Attestation>(base(demandeId, kind))).data;
      } catch (e) {
        if (axios.isAxiosError(e) && e.response?.status === 404) return null;
        throw e;
      }
    },
  });
}

export function useGabarit(demandeId: string, kind: Kind, enabled: boolean) {
  return useQuery({
    queryKey: ['demande', demandeId, 'attestation', kind, 'gabarit'],
    queryFn: async () => (await api.get<Gabarit>(base(demandeId, kind) + 'gabarit/')).data,
    enabled,
  });
}

function useInvalider(demandeId: string) {
  const qc = useQueryClient();
  return () => void qc.invalidateQueries({ queryKey: ['demande', demandeId] });
}

export function useEnregistrerAttestation(demandeId: string, kind: Kind) {
  const invalider = useInvalider(demandeId);
  return useMutation({
    mutationFn: async (payload: { contenu_html: string; contenu_json: unknown }) =>
      (await api.put<Attestation>(base(demandeId, kind), payload)).data,
    onSuccess: invalider,
  });
}

/** Convertit une réponse binaire en URL `blob:` affichable dans un iframe (à révoquer après usage). */
function urlObjet(donnees: Blob): string {
  return URL.createObjectURL(new Blob([donnees], { type: 'application/pdf' }));
}

/**
 * Aperçu de l'attestation : le PDF lui-même, généré par le même moteur et le même gabarit que l'export,
 * à partir du contenu affiché dans l'éditeur. Renvoie une URL `blob:`.
 */
export function usePrevisualiser(demandeId: string, kind: Kind) {
  return useMutation({
    mutationFn: async (contenu_html?: string) =>
      urlObjet(
        (
          await api.post<Blob>(
            base(demandeId, kind) + 'previsualiser/',
            contenu_html ? { contenu_html } : {},
            {
              params: { sortie: 'pdf' },
              responseType: 'blob',
            },
          )
        ).data,
      ),
  });
}

/** PDF enregistré (projet soumis, attestation définitive validée) sous forme d'URL `blob:`. */
export function usePdfAttestation(demandeId: string, kind: Kind, enabled: boolean) {
  return useQuery({
    queryKey: ['demande', demandeId, 'attestation', kind, 'pdf'],
    queryFn: async () =>
      urlObjet((await api.get<Blob>(base(demandeId, kind) + 'pdf/', { responseType: 'blob' })).data),
    enabled,
    staleTime: Infinity,
  });
}

export function useAnalyser(demandeId: string, kind: Kind) {
  const invalider = useInvalider(demandeId);
  return useMutation({
    mutationFn: async () => (await api.post<AnalyseIA>(base(demandeId, kind) + 'analyser/')).data,
    onSuccess: invalider,
  });
}

export function useValiderAttestation(demandeId: string, kind: Kind) {
  const invalider = useInvalider(demandeId);
  return useMutation({
    mutationFn: async (payload: { forcer?: boolean; justification?: string } = {}) =>
      (await api.post<Attestation>(base(demandeId, kind) + 'valider/', payload)).data,
    onSuccess: invalider,
  });
}

/** Distributeur : soumet le projet au siège (notification + email). */
export function useSoumettreProjet(demandeId: string) {
  const invalider = useInvalider(demandeId);
  return useMutation({
    mutationFn: async () => (await api.post<Attestation>(base(demandeId, 'projet') + 'soumettre/')).data,
    onSuccess: invalider,
  });
}

/** Siège : renvoie le projet soumis au distributeur avec un commentaire. */
export function useDemanderCorrectionProjet(demandeId: string) {
  const invalider = useInvalider(demandeId);
  return useMutation({
    mutationFn: async (commentaire: string) =>
      (await api.post<Attestation>(base(demandeId, 'projet') + 'demander-correction/', { commentaire })).data,
    onSuccess: invalider,
  });
}

export function useRouvrirAttestation(demandeId: string, kind: Kind) {
  const invalider = useInvalider(demandeId);
  return useMutation({
    mutationFn: async () => (await api.post<Attestation>(base(demandeId, kind) + 'rouvrir/')).data,
    onSuccess: invalider,
  });
}

export const urlPdfAttestation = (demandeId: string, kind: Kind) => base(demandeId, kind) + 'pdf/';
