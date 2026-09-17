// Extension TipTap : retrait de paragraphe (marge gauche par pas de 5 mm), rendu en style inline `margin-left`
// accepté par le filtre du serveur et par WeasyPrint.
import { Extension } from '@tiptap/core';

export const PAS_RETRAIT_MM = 5;
export const RETRAIT_MAX = 8;

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    retrait: {
      augmenterRetrait: () => ReturnType;
      diminuerRetrait: () => ReturnType;
    };
  }
}

/** Convertit un `margin-left` CSS (mm ou px) en nombre de pas de retrait. */
export function retraitDepuisStyle(marginLeft: string | null | undefined): number {
  if (!marginLeft) return 0;
  const m = /^(-?\d+(?:\.\d+)?)(mm|px|pt)$/.exec(marginLeft.trim());
  if (!m) return 0;
  const valeur = Number(m[1]);
  const mm = m[2] === 'mm' ? valeur : m[2] === 'pt' ? valeur * 0.3528 : valeur * 0.2646;
  return Math.max(0, Math.min(RETRAIT_MAX, Math.round(mm / PAS_RETRAIT_MM)));
}

export const Retrait = Extension.create({
  name: 'retrait',

  addGlobalAttributes() {
    return [
      {
        types: ['paragraph', 'heading'],
        attributes: {
          retrait: {
            default: 0,
            parseHTML: (el) => retraitDepuisStyle((el as HTMLElement).style.marginLeft),
            renderHTML: (attrs) =>
              attrs.retrait > 0 ? { style: `margin-left: ${attrs.retrait * PAS_RETRAIT_MM}mm` } : {},
          },
        },
      },
    ];
  },

  addCommands() {
    const modifier =
      (delta: number) =>
      () =>
      ({
        editor,
        commands,
      }: {
        editor: import('@tiptap/core').Editor;
        commands: import('@tiptap/core').SingleCommands;
      }) => {
        const type = editor.isActive('heading') ? 'heading' : 'paragraph';
        const actuel = Number(editor.getAttributes(type).retrait ?? 0);
        const nouveau = Math.max(0, Math.min(RETRAIT_MAX, actuel + delta));
        if (nouveau === actuel) return false;
        return commands.updateAttributes(type, { retrait: nouveau });
      };
    return {
      augmenterRetrait: modifier(1),
      diminuerRetrait: modifier(-1),
    };
  },

  addKeyboardShortcuts() {
    return {
      'Mod-]': () => this.editor.commands.augmenterRetrait(),
      'Mod-[': () => this.editor.commands.diminuerRetrait(),
    };
  },
});
