// Extension TipTap : surlignage des incohérences détectées par l'analyse IA (décorations ProseMirror).
// Les extraits sont recherchés dans le texte du document ; la couleur dépend de la sévérité.
import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import type { Node as PmNode } from '@tiptap/pm/model';
import type { Incoherence } from '@/api/types';

export const surlignageKey = new PluginKey<DecorationSet>('highlight-incoherences');

interface Cible {
  extrait: string;
  severite: Incoherence['severite'];
  code: string;
}

/** Construit les décorations : chaque occurrence d'un extrait est surlignée. */
function construire(doc: PmNode, cibles: Cible[]): DecorationSet {
  if (cibles.length === 0) return DecorationSet.empty;
  const decorations: Decoration[] = [];
  doc.descendants((node, pos) => {
    if (!node.isText || !node.text) return;
    const texte = node.text;
    for (const cible of cibles) {
      let index = texte.toLowerCase().indexOf(cible.extrait.toLowerCase());
      while (index >= 0) {
        decorations.push(
          Decoration.inline(pos + index, pos + index + cible.extrait.length, {
            class: `ia-highlight ia-highlight--${cible.severite.toLowerCase()}`,
            'data-code': cible.code,
            title: cible.code,
          }),
        );
        index = texte.toLowerCase().indexOf(cible.extrait.toLowerCase(), index + cible.extrait.length);
      }
    }
  });
  return DecorationSet.create(doc, decorations);
}

export const SurlignageIA = Extension.create({
  name: 'highlightIncoherences',

  addProseMirrorPlugins() {
    return [
      new Plugin<DecorationSet>({
        key: surlignageKey,
        state: {
          init: () => DecorationSet.empty,
          apply(tr, ancien) {
            const cibles = tr.getMeta(surlignageKey) as Cible[] | undefined;
            if (cibles) return construire(tr.doc, cibles);
            return tr.docChanged ? ancien.map(tr.mapping, tr.doc) : ancien;
          },
        },
        props: {
          decorations(state) {
            return surlignageKey.getState(state);
          },
        },
      }),
    ];
  },
});

/** Extrait les cibles surlignables d'un résultat d'analyse. */
export function ciblesDepuisIncoherences(incoherences: Incoherence[]): Cible[] {
  return incoherences
    .filter((i) => i.extrait && i.extrait.trim().length >= 2)
    .map((i) => ({ extrait: i.extrait as string, severite: i.severite, code: i.code }));
}
