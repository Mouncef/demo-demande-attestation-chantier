// Extension TipTap : nœud inline atomique « variable » (zone dynamique pré-remplie depuis le FDR).
// Rendu HTML : <span data-variable="cle" data-label="Libellé">valeur</span> – non éditable, supprimable.
import { mergeAttributes, Node } from '@tiptap/core';

export interface VariableOptions {
  valeurs: Record<string, string>;
  libelles: Record<string, string>;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    variable: {
      insererVariable: (cle: string) => ReturnType;
    };
  }
}

export const VariableNode = Node.create<VariableOptions>({
  name: 'variable',
  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,

  addOptions() {
    return { valeurs: {}, libelles: {} };
  },

  addAttributes() {
    return {
      cle: {
        default: null,
        parseHTML: (el) => el.getAttribute('data-variable'),
        renderHTML: (attrs) => ({ 'data-variable': attrs.cle }),
      },
      valeur: {
        default: '',
        parseHTML: (el) => el.textContent ?? '',
        renderHTML: () => ({}),
      },
    };
  },

  parseHTML() {
    return [{ tag: 'span[data-variable]' }];
  },

  renderHTML({ node, HTMLAttributes }) {
    const cle = node.attrs.cle as string;
    const valeur = this.options.valeurs[cle] ?? (node.attrs.valeur as string) ?? '';
    return [
      'span',
      mergeAttributes(HTMLAttributes, {
        'data-label': this.options.libelles[cle] ?? cle,
        title: `Zone dynamique : ${this.options.libelles[cle] ?? cle}`,
        class: 'variable-chip',
        contenteditable: 'false',
      }),
      valeur,
    ];
  },

  renderText({ node }) {
    const cle = node.attrs.cle as string;
    return this.options.valeurs[cle] ?? (node.attrs.valeur as string) ?? '';
  },

  addCommands() {
    return {
      insererVariable:
        (cle: string) =>
        ({ commands }) =>
          commands.insertContent({
            type: this.name,
            attrs: { cle, valeur: this.options.valeurs[cle] ?? '' },
          }),
    };
  },
});
