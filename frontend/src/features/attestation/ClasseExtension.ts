// Extension TipTap : conserve l'attribut `class` des blocs du format officiel AXA (titre centré,
// sections alignées à droite, tableau de garanties, notes, bloc signature) entre le gabarit,
// l'éditeur et le HTML enregistré (la liste blanche du backend autorise `class` sur ces balises).
import { Extension } from '@tiptap/core';

const TYPES = [
  'heading',
  'paragraph',
  'table',
  'tableRow',
  'tableCell',
  'tableHeader',
  'bulletList',
  'orderedList',
  'listItem',
];

export const ClasseExtension = Extension.create({
  name: 'classeConservee',
  addGlobalAttributes() {
    return [
      {
        types: TYPES,
        attributes: {
          class: {
            default: null,
            parseHTML: (el) => el.getAttribute('class'),
            renderHTML: (attrs) => (attrs.class ? { class: attrs.class as string } : {}),
          },
        },
      },
    ];
  },
});
