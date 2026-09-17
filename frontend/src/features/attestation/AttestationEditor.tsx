// Écran 6 : éditeur WYSIWYG (TipTap) de l'attestation : barre d'outils complète, zones dynamiques, surlignage IA,
// feuille A4 reprenant le markup et la feuille de style du PDF (rendu identique au fichier), zoom et plein écran.
import { useEffect, useMemo, useRef, useState } from 'react';
import { EditorContent, useEditor, type Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { Table, TableCell, TableHeader, TableRow } from '@tiptap/extension-table';
import { TextStyleKit } from '@tiptap/extension-text-style';
import TextAlign from '@tiptap/extension-text-align';
import Subscript from '@tiptap/extension-subscript';
import Superscript from '@tiptap/extension-superscript';
import Image from '@tiptap/extension-image';
import Link from '@tiptap/extension-link';
import { CharacterCount, Placeholder } from '@tiptap/extensions';
import type { EnteteAttestation, Incoherence } from '@/api/types';
import { BarreOutils } from './BarreOutils';
import { cssFeuille } from './cssFeuille';
import { ClasseExtension } from './extensions/ClasseExtension';
import { IMAGE_TAILLE_MAX, IMAGE_TYPES } from './extensions/polices';
import { RechercherRemplacer } from './extensions/RechercherRemplacer';
import { Retrait } from './extensions/Retrait';
import { SautPage } from './extensions/SautPage';
import { SurlignageIA, ciblesDepuisIncoherences, surlignageKey } from './extensions/SurlignageIA';
import { VariableNode } from './extensions/VariableNode';
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

/** Cellules de tableau avec couleur de fond (style inline accepté par le serveur et le PDF). */
const attributsCellule = {
  backgroundColor: {
    default: null,
    parseHTML: (el: HTMLElement) => el.style.backgroundColor || null,
    renderHTML: (attrs: Record<string, unknown>) =>
      attrs.backgroundColor ? { style: `background-color: ${attrs.backgroundColor as string}` } : {},
  },
};
const CelluleTableau = TableCell.extend({
  addAttributes() {
    return { ...this.parent?.(), ...attributsCellule };
  },
});
const EnTeteTableau = TableHeader.extend({
  addAttributes() {
    return { ...this.parent?.(), ...attributsCellule };
  },
});

/** Image incorporée (data URL PNG / JPEG) avec largeur relative. */
const ImageDocument = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      width: {
        default: null,
        parseHTML: (el: HTMLElement) => el.getAttribute('width') || el.style.width || null,
        renderHTML: (attrs: Record<string, unknown>) =>
          attrs.width ? { width: attrs.width as string, style: `width: ${attrs.width as string}` } : {},
      },
    };
  },
});

/** Lit un fichier image collé ou déposé et l'insère dans l'éditeur (mêmes limites que la barre d'outils). */
function insererFichierImage(editor: Editor, fichier: File, position?: number): boolean {
  if (!IMAGE_TYPES.includes(fichier.type) || fichier.size > IMAGE_TAILLE_MAX) return false;
  const lecteur = new FileReader();
  lecteur.onload = () => {
    const attrs = { src: String(lecteur.result), alt: fichier.name };
    if (position !== undefined)
      editor.chain().focus().insertContentAt(position, { type: 'image', attrs }).run();
    else editor.chain().focus().setImage(attrs).run();
  };
  lecteur.readAsDataURL(fichier);
  return true;
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
  const [zoom, setZoom] = useState(100);
  const [pleinEcran, setPleinEcran] = useState(false);
  const [rechercheOuverte, setRechercheOuverte] = useState(false);
  const [lienOuvert, setLienOuvert] = useState(false);
  const editorRef = useRef<Editor | null>(null);

  const extensions = useMemo(
    () => [
      // Pas de blocs de code dans une attestation ; les liens sont gérés par l'extension dédiée (https).
      StarterKit.configure({ link: false, codeBlock: false, code: false, heading: { levels: [1, 2, 3] } }),
      Table.configure({ resizable: false }),
      TableRow,
      CelluleTableau,
      EnTeteTableau,
      TextStyleKit,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Subscript,
      Superscript,
      ImageDocument.configure({ allowBase64: true, inline: false }),
      Link.configure({
        openOnClick: false,
        autolink: false,
        linkOnPaste: false,
        defaultProtocol: 'https',
        isAllowedUri: (url) => /^https:\/\//i.test(url),
        HTMLAttributes: { rel: 'noopener noreferrer' },
      }),
      CharacterCount,
      Placeholder.configure({ placeholder: 'Rédigez le contenu de l’attestation…' }),
      Retrait,
      SautPage,
      RechercherRemplacer,
      VariableNode.configure({ valeurs: variables, libelles: libellesVariables }),
      ClasseExtension,
      SurlignageIA,
    ],
    [variables, libellesVariables],
  );

  const editor = useEditor(
    {
      extensions,
      content: contenuInitial,
      editable: !lectureSeule,
      immediatelyRender: false,
      editorProps: {
        attributes: { class: 'editeur', 'aria-label': "Contenu de l'attestation" },
        // Raccourcis d'écran : Ctrl+F (recherche), Ctrl+K (lien), Échap (plein écran).
        handleKeyDown: (_vue, evenement) => {
          const mod = evenement.ctrlKey || evenement.metaKey;
          if (mod && evenement.key.toLowerCase() === 'f') {
            evenement.preventDefault();
            setRechercheOuverte(true);
            return true;
          }
          if (mod && evenement.key.toLowerCase() === 'k') {
            evenement.preventDefault();
            setLienOuvert(true);
            return true;
          }
          if (evenement.key === 'Escape') setPleinEcran(false);
          return false;
        },
        // Images collées ou déposées : lues en data URL (PNG / JPEG, 1 Mo).
        handlePaste: (_vue, evenement) => {
          const fichier = Array.from(evenement.clipboardData?.files ?? []).find((f) =>
            f.type.startsWith('image/'),
          );
          if (!fichier || !editorRef.current) return false;
          return insererFichierImage(editorRef.current, fichier);
        },
        handleDrop: (vue, evenement) => {
          const fichier = Array.from(evenement.dataTransfer?.files ?? []).find((f) =>
            f.type.startsWith('image/'),
          );
          if (!fichier || !editorRef.current) return false;
          const position = vue.posAtCoords({ left: evenement.clientX, top: evenement.clientY })?.pos;
          return insererFichierImage(editorRef.current, fichier, position);
        },
      },
    },
    [contenuInitial, lectureSeule],
  );
  useEffect(() => {
    editorRef.current = editor;
  }, [editor]);

  useEffect(() => {
    onEditor(editor);
    return () => onEditor(null);
  }, [editor, onEditor]);

  // Applique les surlignages à chaque nouveau résultat d'analyse.
  useEffect(() => {
    if (!editor) return;
    const tr = editor.state.tr.setMeta(surlignageKey, ciblesDepuisIncoherences(incoherences));
    editor.view.dispatch(tr);
  }, [editor, incoherences]);

  // Plein écran : verrouille le défilement de la page derrière l'éditeur.
  useEffect(() => {
    document.body.style.overflow = pleinEcran ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [pleinEcran]);

  // La feuille garde la largeur exacte d'une page A4 (même habillage du texte que le PDF) : lorsque la colonne
  // est plus étroite, elle est réduite à l'échelle plutôt que réagencée ; le zoom multiplie ce facteur.
  const cadreRef = useRef<HTMLDivElement>(null);
  const feuilleRef = useRef<HTMLDivElement>(null);
  const [echelle, setEchelle] = useState({ k: 1, hauteur: 0 });
  useEffect(() => {
    const cadre = cadreRef.current;
    const feuille = feuilleRef.current;
    if (!cadre || !feuille) return;
    const ajuster = () => {
      const k = Math.min(1, cadre.clientWidth / feuille.offsetWidth) * (zoom / 100);
      setEchelle({ k, hauteur: feuille.offsetHeight * k });
    };
    const observateur = new ResizeObserver(ajuster);
    observateur.observe(cadre);
    observateur.observe(feuille);
    ajuster();
    return () => observateur.disconnect();
  }, [editor, zoom]);

  if (!editor) return null;

  return (
    <div className={`editeur-wrap ${pleinEcran ? 'editeur-wrap--plein-ecran' : ''}`}>
      {!lectureSeule && (
        <BarreOutils
          editor={editor}
          zoom={zoom}
          onZoom={setZoom}
          pleinEcran={pleinEcran}
          onPleinEcran={setPleinEcran}
          rechercheOuverte={rechercheOuverte}
          onRechercheOuverte={setRechercheOuverte}
          lienOuvert={lienOuvert}
          onLienOuvert={setLienOuvert}
        />
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
