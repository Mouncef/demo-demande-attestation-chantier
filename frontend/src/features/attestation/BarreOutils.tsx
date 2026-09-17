// Barre d'outils WYSIWYG de l'éditeur d'attestation (type traitement de texte) : historique, styles, police,
// caractères, paragraphe, tableau, insertion, outils. Chaque option produit du HTML accepté par la
// sanitisation du serveur et rendu à l'identique dans le PDF.
import { useEffect, useRef, useState, type ChangeEvent } from 'react';
import { useEditorState, type Editor } from '@tiptap/react';
import { Button, Field, Input, Menu, Modal, Select, useToast } from '@/design-system/components';
import { formatDate } from '@/lib/format';
import {
  CARACTERES_SPECIAUX,
  COULEURS,
  IMAGE_TAILLE_MAX,
  IMAGE_TYPES,
  INTERLIGNES,
  LARGEURS_IMAGE,
  POLICES,
  TAILLES_PT,
  ZOOMS,
} from './extensions/polices';
import { rechercheKey } from './extensions/RechercherRemplacer';

interface Props {
  editor: Editor;
  zoom: number;
  onZoom: (zoom: number) => void;
  pleinEcran: boolean;
  onPleinEcran: (actif: boolean) => void;
  rechercheOuverte: boolean;
  onRechercheOuverte: (ouverte: boolean) => void;
  lienOuvert: boolean;
  onLienOuvert: (ouvert: boolean) => void;
}

/** Bouton d'outil : état actif, infobulle avec raccourci. */
function Outil({
  label,
  titre,
  actif,
  disabled,
  onClick,
  className = '',
}: {
  label: React.ReactNode;
  titre: string;
  actif?: boolean;
  disabled?: boolean;
  onClick: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      className={`toolbar__btn ${actif ? 'toolbar__btn--actif' : ''} ${className}`}
      onMouseDown={(e) => e.preventDefault()} // conserve la sélection de l'éditeur
      onClick={onClick}
      disabled={disabled}
      title={titre}
      aria-label={titre}
      aria-pressed={actif}
    >
      {label}
    </button>
  );
}

/** Palette de couleurs de la charte + couleur libre. */
function Palette({
  onChoisir,
  onEffacer,
  fermer,
}: {
  onChoisir: (couleur: string) => void;
  onEffacer: () => void;
  fermer: () => void;
}) {
  const [libre, setLibre] = useState('#00008f');
  return (
    <div className="palette">
      <div className="palette__grille" role="group" aria-label="Couleurs de la charte">
        {COULEURS.map((c) => (
          <button
            key={c.valeur}
            type="button"
            className="palette__pastille"
            style={{ background: c.valeur }}
            title={c.nom}
            aria-label={c.nom}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => {
              onChoisir(c.valeur);
              fermer();
            }}
          />
        ))}
      </div>
      <div className="palette__libre">
        <input
          type="color"
          value={libre}
          onChange={(e) => setLibre(e.target.value)}
          aria-label="Couleur personnalisée"
        />
        <Button
          variante="secondary"
          taille="sm"
          onClick={() => {
            onChoisir(libre);
            fermer();
          }}
        >
          Appliquer
        </Button>
        <Button
          variante="ghost"
          taille="sm"
          onClick={() => {
            onEffacer();
            fermer();
          }}
        >
          Aucune
        </Button>
      </div>
    </div>
  );
}

/** Grille de choix des dimensions d'un tableau à insérer (jusqu'à 8 × 8). */
function GrilleTableau({ onChoisir }: { onChoisir: (lignes: number, colonnes: number) => void }) {
  const [survol, setSurvol] = useState({ l: 0, c: 0 });
  return (
    <div className="grille-tableau" onMouseLeave={() => setSurvol({ l: 0, c: 0 })}>
      <div className="grille-tableau__cases">
        {Array.from({ length: 64 }, (_, i) => {
          const l = Math.floor(i / 8) + 1;
          const c = (i % 8) + 1;
          return (
            <button
              key={i}
              type="button"
              className={`grille-tableau__case ${l <= survol.l && c <= survol.c ? 'grille-tableau__case--active' : ''}`}
              aria-label={`${l} lignes × ${c} colonnes`}
              onMouseEnter={() => setSurvol({ l, c })}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => onChoisir(l, c)}
            />
          );
        })}
      </div>
      <div className="small muted">
        {survol.l ? `${survol.l} ligne(s) × ${survol.c} colonne(s)` : 'Choisir les dimensions'}
      </div>
    </div>
  );
}

export function BarreOutils({
  editor,
  zoom,
  onZoom,
  pleinEcran,
  onPleinEcran,
  rechercheOuverte,
  onRechercheOuverte,
  lienOuvert,
  onLienOuvert,
}: Props) {
  const toast = useToast();
  const fichierRef = useRef<HTMLInputElement>(null);
  // État de l'éditeur suivi à chaque transaction (sélection, marques actives, compteurs, recherche).
  const etat = useEditorState({
    editor,
    selector: ({ editor: e }) => {
      const recherche = rechercheKey.getState(e.state);
      const stockage = e.storage as unknown as {
        characterCount?: { characters: () => number; words: () => number };
      };
      return {
        gras: e.isActive('bold'),
        italique: e.isActive('italic'),
        souligne: e.isActive('underline'),
        barre: e.isActive('strike'),
        exposant: e.isActive('superscript'),
        indice: e.isActive('subscript'),
        titre: e.isActive('heading', { level: 1 })
          ? 'h1'
          : e.isActive('heading', { level: 2 })
            ? 'h2'
            : e.isActive('heading', { level: 3 })
              ? 'h3'
              : e.isActive('blockquote')
                ? 'citation'
                : 'p',
        police: (e.getAttributes('textStyle').fontFamily as string | undefined) ?? '',
        taille: (e.getAttributes('textStyle').fontSize as string | undefined) ?? '',
        interligne: (e.getAttributes('textStyle').lineHeight as string | undefined) ?? '',
        alignement:
          (['left', 'center', 'right', 'justify'] as const).find((a) => e.isActive({ textAlign: a })) ??
          'left',
        puces: e.isActive('bulletList'),
        numeros: e.isActive('orderedList'),
        dansListe: e.isActive('listItem'),
        dansTableau: e.isActive('table'),
        imageSelectionnee: e.isActive('image'),
        lien: e.isActive('link'),
        peutAnnuler: e.can().undo(),
        peutRetablir: e.can().redo(),
        peutFusionner: e.can().mergeCells(),
        peutScinder: e.can().splitCell(),
        caracteres: stockage.characterCount?.characters() ?? 0,
        mots: stockage.characterCount?.words() ?? 0,
        occurrences: recherche?.occurrences.length ?? 0,
        courant: recherche?.courant ?? 0,
      };
    },
  });

  // --- Recherche / remplacement ---
  const [terme, setTerme] = useState('');
  const [remplacement, setRemplacement] = useState('');
  const [sensibleCasse, setSensibleCasse] = useState(false);
  useEffect(() => {
    editor.commands.definirRecherche(rechercheOuverte ? terme : '', sensibleCasse);
  }, [editor, terme, sensibleCasse, rechercheOuverte]);

  // --- Image ---
  const insererImage = (e: ChangeEvent<HTMLInputElement>) => {
    const fichier = e.target.files?.[0];
    e.target.value = '';
    if (!fichier) return;
    if (!IMAGE_TYPES.includes(fichier.type)) {
      toast.notifier('Seules les images PNG et JPEG sont acceptées.', 'error');
      return;
    }
    if (fichier.size > IMAGE_TAILLE_MAX) {
      toast.notifier('Image trop volumineuse (1 Mo maximum).', 'error');
      return;
    }
    const lecteur = new FileReader();
    lecteur.onload = () => {
      editor
        .chain()
        .focus()
        .setImage({ src: String(lecteur.result), alt: fichier.name })
        .run();
    };
    lecteur.readAsDataURL(fichier);
  };

  const chain = () => editor.chain().focus();
  const titreCourant = etat.titre;

  return (
    <div className="toolbar" role="toolbar" aria-label="Mise en forme">
      {/* Historique */}
      <div className="toolbar__groupe">
        <Outil
          label="↶"
          titre="Annuler (Ctrl+Z)"
          disabled={!etat.peutAnnuler}
          onClick={() => chain().undo().run()}
        />
        <Outil
          label="↷"
          titre="Rétablir (Ctrl+Y)"
          disabled={!etat.peutRetablir}
          onClick={() => chain().redo().run()}
        />
      </div>

      {/* Styles de bloc */}
      <div className="toolbar__groupe">
        <Select
          className="toolbar__select"
          value={titreCourant}
          aria-label="Style de paragraphe"
          title="Style de paragraphe"
          onChange={(e) => {
            const v = e.target.value;
            if (v === 'p') chain().setParagraph().run();
            else if (v === 'citation') chain().toggleBlockquote().run();
            else
              chain()
                .toggleHeading({ level: Number(v.slice(1)) as 1 | 2 | 3 })
                .run();
          }}
        >
          <option value="p">Paragraphe</option>
          <option value="h1">Titre 1</option>
          <option value="h2">Titre 2</option>
          <option value="h3">Titre 3</option>
          <option value="citation">Citation</option>
        </Select>
        <Select
          className="toolbar__select toolbar__select--police"
          value={etat.police}
          aria-label="Police"
          title="Police"
          onChange={(e) =>
            e.target.value ? chain().setFontFamily(e.target.value).run() : chain().unsetFontFamily().run()
          }
        >
          <option value="">Police du document</option>
          {POLICES.map((p) => (
            <option key={p.valeur} value={p.valeur}>
              {p.libelle}
            </option>
          ))}
        </Select>
        <Select
          className="toolbar__select toolbar__select--taille"
          value={etat.taille}
          aria-label="Taille"
          title="Taille du texte (points)"
          onChange={(e) =>
            e.target.value ? chain().setFontSize(e.target.value).run() : chain().unsetFontSize().run()
          }
        >
          <option value="">Taille</option>
          {TAILLES_PT.map((t) => (
            <option key={t} value={`${t}pt`}>
              {t} pt
            </option>
          ))}
        </Select>
        <Select
          className="toolbar__select toolbar__select--taille"
          value={etat.interligne}
          aria-label="Interligne"
          title="Interligne"
          onChange={(e) =>
            e.target.value ? chain().setLineHeight(e.target.value).run() : chain().unsetLineHeight().run()
          }
        >
          <option value="">Interligne</option>
          {INTERLIGNES.map((i) => (
            <option key={i.valeur} value={i.valeur}>
              {i.libelle}
            </option>
          ))}
        </Select>
      </div>

      {/* Caractères */}
      <div className="toolbar__groupe">
        <Outil
          label={<b>G</b>}
          titre="Gras (Ctrl+B)"
          actif={etat.gras}
          onClick={() => chain().toggleBold().run()}
        />
        <Outil
          label={<i>I</i>}
          titre="Italique (Ctrl+I)"
          actif={etat.italique}
          onClick={() => chain().toggleItalic().run()}
        />
        <Outil
          label={<u>S</u>}
          titre="Souligné (Ctrl+U)"
          actif={etat.souligne}
          onClick={() => chain().toggleUnderline().run()}
        />
        <Outil
          label={<s>B</s>}
          titre="Barré (Ctrl+Shift+S)"
          actif={etat.barre}
          onClick={() => chain().toggleStrike().run()}
        />
        <Outil
          label={
            <span>
              x<sup>2</sup>
            </span>
          }
          titre="Exposant (Ctrl+.)"
          actif={etat.exposant}
          onClick={() => chain().toggleSuperscript().run()}
        />
        <Outil
          label={
            <span>
              x<sub>2</sub>
            </span>
          }
          titre="Indice (Ctrl+,)"
          actif={etat.indice}
          onClick={() => chain().toggleSubscript().run()}
        />
        <Menu libelle={<span className="toolbar__ico-couleur">A</span>} titre="Couleur du texte">
          {(fermer) => (
            <Palette
              onChoisir={(c) => chain().setColor(c).run()}
              onEffacer={() => chain().unsetColor().run()}
              fermer={fermer}
            />
          )}
        </Menu>
        <Menu libelle={<span className="toolbar__ico-surligneur">ab</span>} titre="Surlignage">
          {(fermer) => (
            <Palette
              onChoisir={(c) => chain().setBackgroundColor(c).run()}
              onEffacer={() => chain().unsetBackgroundColor().run()}
              fermer={fermer}
            />
          )}
        </Menu>
        <Outil
          label="Tx"
          titre="Effacer la mise en forme"
          onClick={() => chain().unsetAllMarks().clearNodes().run()}
        />
      </div>

      {/* Paragraphe */}
      <div className="toolbar__groupe">
        <Outil
          label="≡"
          titre="Aligner à gauche (Ctrl+Shift+L)"
          actif={etat.alignement === 'left'}
          onClick={() => chain().setTextAlign('left').run()}
        />
        <Outil
          label="☰"
          titre="Centrer (Ctrl+Shift+E)"
          actif={etat.alignement === 'center'}
          onClick={() => chain().setTextAlign('center').run()}
        />
        <Outil
          label="≣"
          titre="Aligner à droite (Ctrl+Shift+R)"
          actif={etat.alignement === 'right'}
          onClick={() => chain().setTextAlign('right').run()}
        />
        <Outil
          label="▤"
          titre="Justifier (Ctrl+Shift+J)"
          actif={etat.alignement === 'justify'}
          onClick={() => chain().setTextAlign('justify').run()}
        />
        <Outil
          label="⇤"
          titre="Diminuer le retrait (Ctrl+[)"
          onClick={() =>
            etat.dansListe ? chain().liftListItem('listItem').run() : chain().diminuerRetrait().run()
          }
        />
        <Outil
          label="⇥"
          titre="Augmenter le retrait (Ctrl+])"
          onClick={() =>
            etat.dansListe ? chain().sinkListItem('listItem').run() : chain().augmenterRetrait().run()
          }
        />
        <Outil
          label="• ≡"
          titre="Liste à puces (Ctrl+Shift+8)"
          actif={etat.puces}
          onClick={() => chain().toggleBulletList().run()}
        />
        <Outil
          label="1. ≡"
          titre="Liste numérotée (Ctrl+Shift+7)"
          actif={etat.numeros}
          onClick={() => chain().toggleOrderedList().run()}
        />
        <Outil label="―" titre="Ligne horizontale" onClick={() => chain().setHorizontalRule().run()} />
      </div>

      {/* Tableau */}
      <div className="toolbar__groupe">
        <Menu libelle="▦ Tableau" titre="Tableau" actif={etat.dansTableau}>
          {(fermer) => (
            <div className="menu__liste">
              <GrilleTableau
                onChoisir={(l, c) => {
                  chain().insertTable({ rows: l, cols: c, withHeaderRow: true }).run();
                  fermer();
                }}
              />
              {etat.dansTableau && (
                <>
                  <hr />
                  <button type="button" className="menu__item" onClick={() => chain().addRowBefore().run()}>
                    Insérer une ligne au-dessus
                  </button>
                  <button type="button" className="menu__item" onClick={() => chain().addRowAfter().run()}>
                    Insérer une ligne en dessous
                  </button>
                  <button
                    type="button"
                    className="menu__item"
                    onClick={() => chain().addColumnBefore().run()}
                  >
                    Insérer une colonne à gauche
                  </button>
                  <button type="button" className="menu__item" onClick={() => chain().addColumnAfter().run()}>
                    Insérer une colonne à droite
                  </button>
                  <button type="button" className="menu__item" onClick={() => chain().deleteRow().run()}>
                    Supprimer la ligne
                  </button>
                  <button type="button" className="menu__item" onClick={() => chain().deleteColumn().run()}>
                    Supprimer la colonne
                  </button>
                  <button
                    type="button"
                    className="menu__item"
                    disabled={!etat.peutFusionner}
                    onClick={() => chain().mergeCells().run()}
                  >
                    Fusionner les cellules
                  </button>
                  <button
                    type="button"
                    className="menu__item"
                    disabled={!etat.peutScinder}
                    onClick={() => chain().splitCell().run()}
                  >
                    Scinder la cellule
                  </button>
                  <button
                    type="button"
                    className="menu__item"
                    onClick={() => chain().toggleHeaderRow().run()}
                  >
                    Ligne d'en-tête
                  </button>
                  <div className="menu__item menu__item--statique">
                    Fond de cellule
                    <Palette
                      onChoisir={(c) => chain().setCellAttribute('backgroundColor', c).run()}
                      onEffacer={() => chain().setCellAttribute('backgroundColor', null).run()}
                      fermer={fermer}
                    />
                  </div>
                  <button
                    type="button"
                    className="menu__item menu__item--danger"
                    onClick={() => {
                      chain().deleteTable().run();
                      fermer();
                    }}
                  >
                    Supprimer le tableau
                  </button>
                </>
              )}
            </div>
          )}
        </Menu>
      </div>

      {/* Insertion */}
      <div className="toolbar__groupe">
        <Outil
          label="🖼"
          titre="Insérer une image (PNG ou JPEG, 1 Mo max.)"
          onClick={() => fichierRef.current?.click()}
        />
        <input ref={fichierRef} type="file" accept="image/png,image/jpeg" hidden onChange={insererImage} />
        {etat.imageSelectionnee && (
          <Select
            className="toolbar__select toolbar__select--taille"
            aria-label="Largeur de l'image"
            title="Largeur de l'image"
            value={(editor.getAttributes('image').width as string | undefined) ?? ''}
            onChange={(e) =>
              chain()
                .updateAttributes('image', { width: e.target.value || null })
                .run()
            }
          >
            <option value="">Largeur</option>
            {LARGEURS_IMAGE.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </Select>
        )}
        <Outil label="🔗" titre="Lien https (Ctrl+K)" actif={etat.lien} onClick={() => onLienOuvert(true)} />
        {etat.lien && <Outil label="⛓̸" titre="Retirer le lien" onClick={() => chain().unsetLink().run()} />}
        <Outil
          label="⤓ Page"
          titre={etat.dansTableau ? 'Saut de page (impossible dans un tableau)' : 'Saut de page'}
          disabled={etat.dansTableau}
          onClick={() => chain().insererSautPage().run()}
        />
        <Menu libelle="Ω" titre="Caractère spécial">
          {(fermer) => (
            <div className="caracteres">
              {CARACTERES_SPECIAUX.map((c) => (
                <button
                  key={c}
                  type="button"
                  className="caracteres__item"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => {
                    chain().insertContent(c).run();
                    fermer();
                  }}
                >
                  {c}
                </button>
              ))}
            </div>
          )}
        </Menu>
        <Outil
          label="📅"
          titre="Insérer la date du jour"
          onClick={() => chain().insertContent(formatDate(new Date().toISOString())).run()}
        />
      </div>

      {/* Outils */}
      <div className="toolbar__groupe toolbar__groupe--droite">
        <Outil
          label="🔍"
          titre="Rechercher / remplacer (Ctrl+F)"
          actif={rechercheOuverte}
          onClick={() => onRechercheOuverte(!rechercheOuverte)}
        />
        <Select
          className="toolbar__select toolbar__select--taille"
          value={zoom}
          aria-label="Zoom"
          title="Zoom de la feuille"
          onChange={(e) => onZoom(Number(e.target.value))}
        >
          {ZOOMS.map((z) => (
            <option key={z} value={z}>
              {z} %
            </option>
          ))}
        </Select>
        <Outil
          label={pleinEcran ? '⤡' : '⤢'}
          titre={pleinEcran ? 'Quitter le plein écran (Échap)' : 'Plein écran'}
          actif={pleinEcran}
          onClick={() => onPleinEcran(!pleinEcran)}
        />
        <span className="toolbar__compteur small muted" aria-live="polite">
          {etat.mots} mot{etat.mots > 1 ? 's' : ''} · {etat.caracteres} car.
        </span>
      </div>

      {rechercheOuverte && (
        <div className="recherche" role="search">
          <Input
            value={terme}
            onChange={(e) => setTerme(e.target.value)}
            placeholder="Rechercher…"
            aria-label="Texte à rechercher"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === 'Enter') chain().occurrenceSuivante().run();
              if (e.key === 'Escape') onRechercheOuverte(false);
            }}
          />
          <Input
            value={remplacement}
            onChange={(e) => setRemplacement(e.target.value)}
            placeholder="Remplacer par…"
            aria-label="Texte de remplacement"
          />
          <label className="small">
            <input
              type="checkbox"
              checked={sensibleCasse}
              onChange={(e) => setSensibleCasse(e.target.checked)}
            />{' '}
            Casse
          </label>
          <span className="small muted">
            {etat.occurrences
              ? `${etat.courant + 1} / ${etat.occurrences}`
              : terme
                ? 'Aucune occurrence'
                : ''}
          </span>
          <Button
            variante="ghost"
            taille="sm"
            disabled={!etat.occurrences}
            onClick={() => chain().occurrencePrecedente().run()}
          >
            ↑
          </Button>
          <Button
            variante="ghost"
            taille="sm"
            disabled={!etat.occurrences}
            onClick={() => chain().occurrenceSuivante().run()}
          >
            ↓
          </Button>
          <Button
            variante="secondary"
            taille="sm"
            disabled={!etat.occurrences}
            onClick={() => chain().remplacerOccurrence(remplacement).run()}
          >
            Remplacer
          </Button>
          <Button
            variante="secondary"
            taille="sm"
            disabled={!etat.occurrences}
            onClick={() => chain().toutRemplacer(remplacement).run()}
          >
            Tout remplacer
          </Button>
          <Button
            variante="ghost"
            taille="sm"
            onClick={() => onRechercheOuverte(false)}
            aria-label="Fermer la recherche"
          >
            ✕
          </Button>
        </div>
      )}

      {lienOuvert && <DialogueLien editor={editor} onFermer={() => onLienOuvert(false)} />}
    </div>
  );
}

/** Boîte de dialogue d'insertion de lien https : valeurs initiales lues à l'ouverture (montage). */
function DialogueLien({ editor, onFermer }: { editor: Editor; onFermer: () => void }) {
  const [url, setUrl] = useState(
    () => (editor.getAttributes('link').href as string | undefined) ?? 'https://',
  );
  const [texte, setTexte] = useState(() => {
    const { from, to } = editor.state.selection;
    return editor.state.doc.textBetween(from, to, ' ');
  });
  const [erreur, setErreur] = useState<string | undefined>();
  const valider = () => {
    if (!/^https:\/\/[^\s]+\.[^\s]+/i.test(url)) {
      setErreur('Adresse https:// attendue (ex. https://www.axa.fr).');
      return;
    }
    const chain = editor.chain().focus();
    if (editor.state.selection.empty || !texte) {
      chain
        .insertContent({ type: 'text', text: texte || url, marks: [{ type: 'link', attrs: { href: url } }] })
        .run();
    } else {
      chain.extendMarkRange('link').setLink({ href: url }).run();
    }
    onFermer();
  };
  return (
    <Modal
      ouvert
      titre="Insérer un lien"
      onFermer={onFermer}
      pied={
        <>
          <Button variante="secondary" onClick={onFermer}>
            Annuler
          </Button>
          <Button onClick={valider}>Insérer</Button>
        </>
      }
    >
      <Field label="Adresse (https uniquement)" requis erreur={erreur}>
        {(id) => (
          <Input
            id={id}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://"
            invalide={Boolean(erreur)}
            autoFocus
          />
        )}
      </Field>
      <Field label="Texte affiché" aide="Vide : l'adresse est affichée.">
        {(id) => <Input id={id} value={texte} onChange={(e) => setTexte(e.target.value)} />}
      </Field>
    </Modal>
  );
}
