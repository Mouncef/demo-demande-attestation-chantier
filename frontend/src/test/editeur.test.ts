import { describe, expect, it } from 'vitest';
import { Editor } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import {
  RechercherRemplacer,
  rechercheKey,
  trouverOccurrences,
} from '@/features/attestation/extensions/RechercherRemplacer';
import { Retrait, retraitDepuisStyle } from '@/features/attestation/extensions/Retrait';
import { SautPage } from '@/features/attestation/extensions/SautPage';

function editeur(contenu: string) {
  return new Editor({ extensions: [StarterKit, RechercherRemplacer, Retrait, SautPage], content: contenu });
}

describe('rechercher / remplacer', () => {
  it('trouve les occurrences sans tenir compte de la casse et remplace', () => {
    const e = editeur('<p>Chantier de Lyon. chantier terminé.</p>');
    expect(trouverOccurrences(e.state.doc, 'chantier', false)).toHaveLength(2);
    expect(trouverOccurrences(e.state.doc, 'chantier', true)).toHaveLength(1);
    e.commands.definirRecherche('chantier');
    expect(rechercheKey.getState(e.state)?.occurrences).toHaveLength(2);
    e.commands.remplacerOccurrence('projet');
    expect(e.getText()).toBe('projet de Lyon. chantier terminé.');
    e.commands.toutRemplacer('ouvrage');
    expect(e.getText()).toBe('projet de Lyon. ouvrage terminé.');
    e.destroy();
  });
});

describe('retrait et saut de page', () => {
  it('convertit un margin-left en pas de retrait et le restitue en HTML', () => {
    expect(retraitDepuisStyle('10mm')).toBe(2);
    expect(retraitDepuisStyle('38px')).toBe(2);
    expect(retraitDepuisStyle(null)).toBe(0);
    const e = editeur('<p style="margin-left: 15mm">Texte</p>');
    expect(e.getHTML()).toContain('margin-left: 15mm');
    e.commands.selectAll();
    e.commands.diminuerRetrait();
    expect(e.getHTML()).toContain('margin-left: 10mm');
    e.destroy();
  });

  it('insère et conserve un saut de page', () => {
    const e = editeur('<p>Avant</p>');
    e.commands.setTextSelection(6);
    e.commands.insererSautPage();
    expect(e.getHTML()).toContain('<p>Avant</p><div class="saut-page" data-type="saut-page"></div><p></p>');
    const e2 = editeur('<p>A</p><div class="saut-page"></div><p>B</p>');
    expect(e2.getHTML()).toContain('data-type="saut-page"');
    e.destroy();
    e2.destroy();
  });
});
