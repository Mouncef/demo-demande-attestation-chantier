// Extension TipTap : saut de page explicite. Rendu `<div class="saut-page">` (classe conservée par le serveur) ;
// dans le PDF, `.saut-page { page-break-after: always }` ; à l'écran, une ligne pointillée légendée.
import { Node } from '@tiptap/core';

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    sautPage: {
      insererSautPage: () => ReturnType;
    };
  }
}

export const SautPage = Node.create({
  name: 'sautPage',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: true,

  parseHTML() {
    return [{ tag: 'div.saut-page' }];
  },

  renderHTML() {
    return ['div', { class: 'saut-page', 'data-type': 'saut-page' }];
  },

  addCommands() {
    return {
      insererSautPage:
        () =>
        ({ editor, commands }) => {
          // Un saut de page n'a pas de sens à l'intérieur d'une cellule de tableau.
          if (editor.isActive('table')) return false;
          return commands.insertContent([{ type: this.name }, { type: 'paragraph' }]);
        },
    };
  },
});
