// Écran 6 : éditeur WYSIWYG (TipTap) de l'attestation avec zones dynamiques et surlignage IA.
import { useEffect, useMemo } from 'react';
import { EditorContent, useEditor, type Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { TableKit } from '@tiptap/extension-table';
import type { EnteteAttestation, Incoherence } from '@/api/types';
import { Button } from '@/design-system/components';
import { ClasseExtension } from './ClasseExtension';
import { HighlightExtension, ciblesDepuisIncoherences, highlightKey } from './HighlightExtension';
import { VariableNode } from './VariableNode';
import './editor.css';

export interface Assureur {
  nom: string;
  forme: string;
  rcs: string;
  adresse: string;
  mention: string;
}

interface Props {
  contenuInitial: string;
  assureur?: Assureur;
  /** Cadre du format officiel AXA (intermédiaire, références, destinataire, date) : non modifiable. */
  entete?: EnteteAttestation;
  variables: Record<string, string>;
  libellesVariables: Record<string, string>;
  lectureSeule: boolean;
  incoherences: Incoherence[];
  onEditor: (editor: Editor | null) => void;
}

export function AttestationEditor({
  contenuInitial,
  assureur,
  entete,
  variables,
  libellesVariables,
  lectureSeule,
  incoherences,
  onEditor,
}: Props) {
  const extensions = useMemo(
    () => [
      // Pas de liens ni de blocs de code dans une attestation.
      StarterKit.configure({ link: false, codeBlock: false, code: false }),
      TableKit.configure({ table: { resizable: false } }),
      VariableNode.configure({ valeurs: variables, libelles: libellesVariables }),
      ClasseExtension,
      HighlightExtension,
    ],
    [variables, libellesVariables],
  );

  const editor = useEditor(
    {
      extensions,
      content: contenuInitial,
      editable: !lectureSeule,
      immediatelyRender: false,
      editorProps: { attributes: { class: 'editeur', 'aria-label': "Contenu de l'attestation" } },
    },
    [contenuInitial, lectureSeule],
  );

  useEffect(() => {
    onEditor(editor);
    return () => onEditor(null);
  }, [editor, onEditor]);

  // Applique les surlignages à chaque nouveau résultat d'analyse.
  useEffect(() => {
    if (!editor) return;
    const tr = editor.state.tr.setMeta(highlightKey, ciblesDepuisIncoherences(incoherences));
    editor.view.dispatch(tr);
  }, [editor, incoherences]);

  if (!editor) return null;

  const outil = (label: string, actif: boolean, action: () => void, title: string) => (
    <button
      type="button"
      className={`toolbar__btn ${actif ? 'toolbar__btn--actif' : ''}`}
      onClick={action}
      disabled={lectureSeule}
      title={title}
      aria-pressed={actif}
    >
      {label}
    </button>
  );

  return (
    <div className="editeur-wrap">
      {!lectureSeule && (
        <div className="toolbar" role="toolbar" aria-label="Mise en forme">
          {outil('G', editor.isActive('bold'), () => editor.chain().focus().toggleBold().run(), 'Gras')}
          {outil(
            'I',
            editor.isActive('italic'),
            () => editor.chain().focus().toggleItalic().run(),
            'Italique',
          )}
          {outil(
            'S',
            editor.isActive('underline'),
            () => editor.chain().focus().toggleUnderline().run(),
            'Souligné',
          )}
          <span className="toolbar__sep" />
          {outil(
            'H1',
            editor.isActive('heading', { level: 1 }),
            () => editor.chain().focus().toggleHeading({ level: 1 }).run(),
            'Titre 1',
          )}
          {outil(
            'H2',
            editor.isActive('heading', { level: 2 }),
            () => editor.chain().focus().toggleHeading({ level: 2 }).run(),
            'Titre 2',
          )}
          {outil(
            '¶',
            editor.isActive('paragraph'),
            () => editor.chain().focus().setParagraph().run(),
            'Paragraphe',
          )}
          <span className="toolbar__sep" />
          {outil(
            '• Liste',
            editor.isActive('bulletList'),
            () => editor.chain().focus().toggleBulletList().run(),
            'Liste à puces',
          )}
          {outil(
            '1. Liste',
            editor.isActive('orderedList'),
            () => editor.chain().focus().toggleOrderedList().run(),
            'Liste numérotée',
          )}
          <span className="toolbar__sep" />
          <Button
            variante="ghost"
            taille="sm"
            onClick={() => editor.chain().focus().undo().run()}
            title="Annuler"
          >
            ↶
          </Button>
          <Button
            variante="ghost"
            taille="sm"
            onClick={() => editor.chain().focus().redo().run()}
            title="Rétablir"
          >
            ↷
          </Button>
        </div>
      )}
      <div className="editeur-page">
        <div className="feuille">
          {/* Cadre du format officiel AXA (identique à la première page du PDF) : non modifiable. */}
          <header className="feuille__entete" aria-label="En-tête AXA">
            <div className="feuille__intermediaire">
              <div className="feuille__etiquette">Votre Intermédiaire</div>
              <strong>{entete?.intermediaire.nom ?? '—'}</strong>
              {entete?.intermediaire.adresse.split('\n').map((ligne) => (
                <div key={ligne}>{ligne}</div>
              ))}
              {entete?.intermediaire.telephone && <div>☎ {entete.intermediaire.telephone}</div>}
              {entete && <div>✉ {entete.intermediaire.email}</div>}
            </div>
            <div className="feuille__accroche">
              réinventons <span className="feuille__barre">/</span>
              <br />
              notre métier
            </div>
            <img src="/logo.png" alt="AXA" />
          </header>
          <div className="feuille__references" aria-label="Références du contrat">
            <div>
              <span className="feuille__label">Votre contrat</span>
              <div className="feuille__valeur">{entete?.produit ?? '—'}</div>
              <span className="feuille__label">Vos références</span>
              <div className="feuille__valeur">
                Contrat
                <br />
                <strong>{entete?.numero_contrat || '—'}</strong>
              </div>
              {entete?.reference_client && (
                <div className="feuille__valeur">
                  Référence client
                  <br />
                  <strong>{entete.reference_client}</strong>
                </div>
              )}
            </div>
            <div className="feuille__destinataire">
              <div>
                <strong>{entete?.destinataire.nom || '—'}</strong>
                <br />
                {entete?.destinataire.adresse}
                <br />
                {entete?.destinataire.cp_ville}
              </div>
              <div className="feuille__date">
                Date du courrier
                <br />
                <strong>{entete?.date_courrier ?? ''}</strong>
              </div>
            </div>
          </div>
          <EditorContent editor={editor} />
          <footer className="feuille__pied">
            {entete?.mentions_legales ?? (assureur ? `${assureur.nom} – ${assureur.mention}` : '')}
          </footer>
        </div>
      </div>
    </div>
  );
}
