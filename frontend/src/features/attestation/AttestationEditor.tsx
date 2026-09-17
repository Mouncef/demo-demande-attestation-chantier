// Écran 6 : éditeur WYSIWYG (TipTap) de l'attestation avec zones dynamiques et surlignage IA.
import { useEffect, useMemo, useRef, useState } from 'react';
import { EditorContent, useEditor, type Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { TableKit } from '@tiptap/extension-table';
import type { EnteteAttestation, Incoherence } from '@/api/types';
import { Button } from '@/design-system/components';
import { ClasseExtension } from './ClasseExtension';
import { cssFeuille } from './cssFeuille';
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
  /** Feuille de style du document (celle du PDF) : injectée telle quelle, restreinte à la feuille. */
  cssDocument?: string;
  /** Projet : filigrane PROJET comme sur le PDF. */
  estProjet?: boolean;
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
  cssDocument,
  estProjet = false,
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

  // La feuille garde la largeur exacte d'une page A4 (même habillage du texte que le PDF) : lorsque la colonne
  // est plus étroite, elle est réduite à l'échelle plutôt que réagencée.
  const cadreRef = useRef<HTMLDivElement>(null);
  const feuilleRef = useRef<HTMLDivElement>(null);
  const [echelle, setEchelle] = useState({ k: 1, hauteur: 0 });
  useEffect(() => {
    const cadre = cadreRef.current;
    const feuille = feuilleRef.current;
    if (!cadre || !feuille) return;
    const ajuster = () => {
      const k = Math.min(1, cadre.clientWidth / feuille.offsetWidth);
      setEchelle({ k, hauteur: feuille.offsetHeight * k });
    };
    const observateur = new ResizeObserver(ajuster);
    observateur.observe(cadre);
    observateur.observe(feuille);
    ajuster();
    return () => observateur.disconnect();
  }, [editor]);

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
        {/* La feuille reprend le markup et la feuille de style du gabarit PDF : même rendu que le fichier. */}
        {cssDocument && <style>{cssFeuille(cssDocument)}</style>}
        <div ref={cadreRef} className="feuille-cadre" style={{ height: echelle.hauteur || undefined }}>
          <div
            ref={feuilleRef}
            className={`feuille document-attestation ${lectureSeule ? 'feuille--lecture' : ''}`}
            style={{ transform: `scale(${echelle.k})` }}
          >
            <div className="document">
              {estProjet && <div className="watermark">PROJET</div>}
              <div className="entete" aria-label="En-tête AXA">
                <div className="intermediaire">
                  <div className="etiquette">Votre Intermédiaire</div>
                  <strong>{entete?.intermediaire.nom ?? '—'}</strong>
                  <br />
                  {entete?.intermediaire.adresse.split('\n').map((ligne, i) => (
                    <span key={i}>
                      {ligne}
                      <br />
                    </span>
                  ))}
                  {entete?.intermediaire.telephone && (
                    <>
                      ☎ {entete.intermediaire.telephone}
                      <br />
                    </>
                  )}
                  {entete && <>✉ {entete.intermediaire.email}</>}
                </div>
                <div className="accroche">
                  réinventons <span className="barre">/</span>
                  <br />
                  notre métier
                </div>
                <img className="logo" src="/logo.png" alt="AXA" />
              </div>
              <div className="references" aria-label="Références du contrat">
                <div className="gauche">
                  <span className="label-bleu">Votre contrat</span>
                  <span className="valeur">{entete?.produit ?? '—'}</span>
                  <span className="label-bleu">Vos références</span>
                  <span className="valeur">
                    Contrat
                    <br />
                    <strong>{entete?.numero_contrat || '—'}</strong>
                  </span>
                  {entete?.reference_client && (
                    <span className="valeur">
                      Référence client
                      <br />
                      <strong>{entete.reference_client}</strong>
                    </span>
                  )}
                </div>
                <div className="droite">
                  <div className="destinataire">
                    <strong>{entete?.destinataire.nom || '—'}</strong>
                    <br />
                    {entete?.destinataire.adresse}
                    <br />
                    {entete?.destinataire.cp_ville}
                  </div>
                  <div className="date-courrier">
                    Date du courrier
                    <br />
                    <strong>{entete?.date_courrier ?? ''}</strong>
                  </div>
                </div>
              </div>
              <EditorContent editor={editor} />
              <div className="mentions-legales">
                {entete?.mentions_legales ?? (assureur ? `${assureur.nom} – ${assureur.mention}` : '')}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
