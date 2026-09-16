// Formatage à la française des montants, dates et tailles.

export function formatMontant(valeur: string | number | null | undefined, devise = true): string {
  if (valeur === null || valeur === undefined || valeur === '') return '—';
  const nombre = typeof valeur === 'string' ? Number(valeur) : valeur;
  if (Number.isNaN(nombre)) return '—';
  const texte = new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(nombre);
  return devise ? `${texte} €` : texte;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '—' : new Intl.DateTimeFormat('fr-FR').format(date);
}

export function formatDateHeure(iso: string | null | undefined): string {
  if (!iso) return '—';
  const date = new Date(iso);
  return Number.isNaN(date.getTime())
    ? '—'
    : new Intl.DateTimeFormat('fr-FR', { dateStyle: 'short', timeStyle: 'short' }).format(date);
}

export function formatTaille(octets: number): string {
  if (octets < 1024) return `${octets} o`;
  if (octets < 1024 * 1024) return `${(octets / 1024).toFixed(1)} Ko`;
  return `${(octets / (1024 * 1024)).toFixed(1)} Mo`;
}

/** Durée restante lisible (« 3 h 12 min ») jusqu'à une date ISO, ou null si passée. */
export function dureeRestante(iso: string | null | undefined, maintenant: number = Date.now()): string | null {
  if (!iso) return null;
  const ms = new Date(iso).getTime() - maintenant;
  if (ms <= 0) return null;
  const minutes = Math.ceil(ms / 60_000);
  const heures = Math.floor(minutes / 60);
  return heures > 0 ? `${heures} h ${String(minutes % 60).padStart(2, '0')} min` : `${minutes} min`;
}
