// Extension TipTap : rechercher / remplacer dans le document. Les occurrences sont surlignées par des
// décorations ProseMirror (le contenu n'est pas modifié tant que l'on ne remplace pas) ; l'occurrence courante
// est distinguée et suivie par la sélection.
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey, TextSelection } from '@tiptap/pm/state';
import type { Node as PMNode } from '@tiptap/pm/model';
import { Decoration, DecorationSet } from '@tiptap/pm/view';

export interface Occurrence {
  from: number;
  to: number;
}

export interface EtatRecherche {
  terme: string;
  sensibleCasse: boolean;
  occurrences: Occurrence[];
  courant: number;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    rechercherRemplacer: {
      definirRecherche: (terme: string, sensibleCasse?: boolean) => ReturnType;
      occurrenceSuivante: () => ReturnType;
      occurrencePrecedente: () => ReturnType;
      remplacerOccurrence: (remplacement: string) => ReturnType;
      toutRemplacer: (remplacement: string) => ReturnType;
    };
  }
}

export const rechercheKey = new PluginKey<EtatRecherche>('rechercher-remplacer');

function echapper(terme: string): string {
  return terme.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Toutes les occurrences du terme dans les nœuds texte du document. */
export function trouverOccurrences(doc: PMNode, terme: string, sensibleCasse: boolean): Occurrence[] {
  if (!terme) return [];
  const motif = new RegExp(echapper(terme), sensibleCasse ? 'g' : 'gi');
  const occurrences: Occurrence[] = [];
  doc.descendants((node, pos) => {
    if (!node.isText || !node.text) return;
    for (const m of node.text.matchAll(motif)) {
      if (m.index === undefined || m[0].length === 0) continue;
      occurrences.push({ from: pos + m.index, to: pos + m.index + m[0].length });
    }
  });
  return occurrences;
}

const ETAT_INITIAL: EtatRecherche = { terme: '', sensibleCasse: false, occurrences: [], courant: 0 };

export const RechercherRemplacer = Extension.create({
  name: 'rechercherRemplacer',

  addCommands() {
    const etat = (editor: import('@tiptap/core').Editor) =>
      rechercheKey.getState(editor.state) ?? ETAT_INITIAL;
    const aller =
      (delta: number) =>
      () =>
      ({ editor, tr, dispatch }: import('@tiptap/core').CommandProps) => {
        const e = etat(editor);
        if (e.occurrences.length === 0) return false;
        const courant = (e.courant + delta + e.occurrences.length) % e.occurrences.length;
        if (dispatch) {
          const occ = e.occurrences[courant];
          tr.setMeta(rechercheKey, { ...e, courant });
          tr.setSelection(TextSelection.create(tr.doc, occ.from, occ.to)).scrollIntoView();
        }
        return true;
      };
    return {
      definirRecherche:
        (terme, sensibleCasse = false) =>
        ({ tr, dispatch }) => {
          if (dispatch) tr.setMeta(rechercheKey, { terme, sensibleCasse, courant: 0 });
          return true;
        },
      occurrenceSuivante: aller(1),
      occurrencePrecedente: aller(-1),
      remplacerOccurrence:
        (remplacement) =>
        ({ editor, tr, dispatch }) => {
          const e = etat(editor);
          const occ = e.occurrences[e.courant];
          if (!occ) return false;
          if (dispatch) {
            tr.insertText(remplacement, occ.from, occ.to);
            tr.setMeta(rechercheKey, { ...e, courant: e.courant });
          }
          return true;
        },
      toutRemplacer:
        (remplacement) =>
        ({ editor, tr, dispatch }) => {
          const e = etat(editor);
          if (e.occurrences.length === 0) return false;
          if (dispatch) {
            // De la fin vers le début pour ne pas décaler les positions restantes.
            [...e.occurrences].reverse().forEach((occ) => tr.insertText(remplacement, occ.from, occ.to));
            tr.setMeta(rechercheKey, { ...e, courant: 0 });
          }
          return true;
        },
    };
  },

  addProseMirrorPlugins() {
    return [
      new Plugin<EtatRecherche>({
        key: rechercheKey,
        state: {
          init: () => ETAT_INITIAL,
          apply(tr, precedent) {
            const meta = tr.getMeta(rechercheKey) as Partial<EtatRecherche> | undefined;
            const base = { ...precedent, ...(meta ?? {}) };
            if (!meta && !tr.docChanged) return precedent;
            const occurrences = trouverOccurrences(tr.doc, base.terme, base.sensibleCasse);
            const courant = occurrences.length ? Math.min(base.courant, occurrences.length - 1) : 0;
            return { ...base, occurrences, courant };
          },
        },
        props: {
          decorations(state) {
            const e = rechercheKey.getState(state);
            if (!e || e.occurrences.length === 0) return DecorationSet.empty;
            return DecorationSet.create(
              state.doc,
              e.occurrences.map((occ, i) =>
                Decoration.inline(occ.from, occ.to, {
                  class: i === e.courant ? 'recherche-match recherche-match--courant' : 'recherche-match',
                }),
              ),
            );
          },
        },
      }),
    ];
  },
});
