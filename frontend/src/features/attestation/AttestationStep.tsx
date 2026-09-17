// Orchestration de l'éditeur d'attestation.
//
// Circuit : après acceptation de la demande, le distributeur prépare un PROJET et le soumet au siège
// (notification + email). Le siège reprend le projet soumis comme base de l'attestation DÉFINITIVE,
// la rectifie et la valide (analyse IA), ou renvoie le projet au distributeur pour correction.
// Le distributeur ne voit l'attestation définitive qu'une fois établie par le siège.
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { Editor } from '@tiptap/react';
import { TextSelection } from '@tiptap/pm/state';
import {
  urlPdfAttestation,
  useAnalyser,
  useAttestation,
  useDemanderCorrectionProjet,
  useEnregistrerAttestation,
  useGabarit,
  usePdfAttestation,
  usePrevisualiser,
  useRouvrirAttestation,
  useSoumettreProjet,
  useValiderAttestation,
} from '@/api/attestations';
import { telechargerFichier } from '@/api/client';
import type { DemandeDetail, Incoherence } from '@/api/types';
import { formatDateHeure } from '@/lib/format';
import { LIBELLES_STATUT_ATTESTATION } from '@/lib/libelles';
import { Alert, Badge, Button, Card, Modal, Spinner, Textarea, useToast } from '@/design-system/components';
import { useAuth } from '@/features/auth/AuthContext';
import { AnalysePanel } from './AnalysePanel';
import { AttestationEditor } from './AttestationEditor';

interface Props {
  demande: DemandeDetail;
  kind: 'projet' | 'definitive';
  /** L'utilisateur courant peut-il éditer ce type d'attestation (rôle + état, calculé par l'API) ? */
  peutEditer: boolean;
  /** Siège : ouvre l'onglet de l'attestation définitive (pré-remplie depuis le projet soumis). */
  onEtablirDefinitive?: () => void;
}

export function AttestationStep({ demande, kind, peutEditer, onEtablirDefinitive }: Props) {
  const { utilisateur } = useAuth();
  const estSiege = utilisateur?.role === 'SIEGE';
  const definitiveEtablie = demande.etat_attestation === 'DEFINITIVE';

  // Le distributeur n'a accès à la définitive qu'une fois établie : état d'attente sans éditeur.
  if (kind === 'definitive' && !estSiege && !definitiveEtablie) {
    return (
      <Card titre="🏢 Attestation définitive">
        <Alert type="info">
          <strong>En attente d'établissement par le siège.</strong>{' '}
          {demande.etat_attestation === 'PROJET_SOUMIS'
            ? 'Votre projet a été soumis : le siège le reprend pour établir l’attestation définitive. Vous serez notifié dès qu’elle sera disponible.'
            : demande.etat_attestation === 'PROJET_A_CORRIGER'
              ? 'Le siège vous a renvoyé le projet pour correction : corrigez-le puis soumettez-le à nouveau.'
              : 'Préparez et soumettez votre projet d’attestation depuis l’étape « Projet d’attestation ».'}
        </Alert>
      </Card>
    );
  }
  return (
    <EditeurAttestation
      demande={demande}
      kind={kind}
      peutEditer={peutEditer}
      onEtablirDefinitive={onEtablirDefinitive}
    />
  );
}

function EditeurAttestation({ demande, kind, peutEditer, onEtablirDefinitive }: Props) {
  const toast = useToast();
  const { utilisateur } = useAuth();
  const estSiege = utilisateur?.role === 'SIEGE';
  // L'analyse de cohérence est un outil d'instruction du siège pour établir l'attestation définitive.
  const analyseDisponible = kind === 'definitive' && estSiege;
  const { data: attestation, isLoading } = useAttestation(demande.id, kind);
  // Le gabarit est toujours chargé : il fournit la liste des variables insérables et leurs libellés.
  const { data: gabarit } = useGabarit(demande.id, kind, attestation !== undefined);
  const enregistrer = useEnregistrerAttestation(demande.id, kind);
  const previsualiser = usePrevisualiser(demande.id, kind);
  const analyser = useAnalyser(demande.id, kind);
  const valider = useValiderAttestation(demande.id, kind);
  const soumettre = useSoumettreProjet(demande.id);
  const demanderCorrection = useDemanderCorrectionProjet(demande.id);
  const rouvrir = useRouvrirAttestation(demande.id, kind);
  const [editor, setEditor] = useState<Editor | null>(null);
  // Aperçu : URL `blob:` du PDF généré depuis le contenu affiché (révoquée à la fermeture).
  const [apercu, setApercu] = useState<string | null>(null);
  useEffect(
    () => () => {
      if (apercu) URL.revokeObjectURL(apercu);
    },
    [apercu],
  );
  const [forcage, setForcage] = useState(false);
  const [justification, setJustification] = useState('');
  const [confirmerSoumission, setConfirmerSoumission] = useState(false);
  const [correction, setCorrection] = useState<string | null>(null);
  const [modifie, setModifie] = useState(false);

  const statut = attestation?.statut;
  const validee = statut === 'VALIDEE';
  const soumise = statut === 'SOUMISE';
  const aCorriger = statut === 'A_CORRIGER';
  const definitiveEtablie = demande.etat_attestation === 'DEFINITIVE';
  const lectureSeule = !peutEditer || validee || soumise;
  // Lecture seule avec un PDF enregistré (projet soumis, définitive validée) : on affiche le fichier lui-même.
  const afficherPdf = lectureSeule && Boolean(attestation?.pdf_disponible);
  const { data: pdfEnregistre } = usePdfAttestation(demande.id, kind, afficherPdf);
  const contenuInitial = attestation?.contenu_html ?? gabarit?.contenu_html ?? '';
  const variables = useMemo(() => {
    const brutes = attestation?.variables_snapshot ?? gabarit?.variables ?? {};
    return Object.fromEntries(Object.entries(brutes).filter(([, v]) => typeof v === 'string')) as Record<
      string,
      string
    >;
  }, [attestation?.variables_snapshot, gabarit?.variables]);
  const libelles = useMemo(() => gabarit?.variables_disponibles ?? VARIABLES_PAR_DEFAUT, [gabarit]);
  const analyse = analyseDisponible ? (attestation?.derniere_analyse ?? null) : null;
  const incoherences: Incoherence[] = useMemo(
    () => (analyse && !modifie ? analyse.resultat.incoherences : []),
    [analyse, modifie],
  );

  const onEditor = useCallback((e: Editor | null) => {
    setEditor(e);
    setModifie(false);
    e?.on('update', () => setModifie(true));
  }, []);

  const sauvegarder = async (silencieux = false): Promise<boolean> => {
    if (!editor) return false;
    try {
      await enregistrer.mutateAsync({ contenu_html: editor.getHTML(), contenu_json: editor.getJSON() });
      setModifie(false);
      if (!silencieux) toast.notifier('Attestation enregistrée.', 'success');
      return true;
    } catch (e) {
      toast.erreur(e);
      return false;
    }
  };

  /** Enregistre d'abord si le contenu a changé (ou n'a jamais été enregistré). */
  const enregistrerSiBesoin = async (): Promise<boolean> =>
    lectureSeule || (!modifie && Boolean(attestation)) ? true : sauvegarder(true);

  const lancerAnalyse = async () => {
    if (!(await enregistrerSiBesoin())) return;
    try {
      const res = await analyser.mutateAsync();
      setModifie(false);
      toast.notifier(
        res.statut === 'COHERENT'
          ? 'Analyse terminée : attestation cohérente avec le FDR.'
          : `Analyse terminée : ${res.resultat.incoherences.length} incohérence(s) détectée(s).`,
        res.statut === 'COHERENT' ? 'success' : 'error',
      );
    } catch (e) {
      toast.erreur(e);
    }
  };

  const ouvrirApercu = async () => {
    try {
      // Le PDF est généré depuis ce qui est affiché dans l'éditeur : l'aperçu est le fichier tel qu'il sera exporté.
      setApercu(await previsualiser.mutateAsync(editor ? editor.getHTML() : undefined));
    } catch (e) {
      toast.erreur(e);
    }
  };

  const exporterPdf = async () => {
    if (!(await enregistrerSiBesoin())) return;
    try {
      await telechargerFichier(urlPdfAttestation(demande.id, kind), `attestation-${demande.reference}.pdf`);
    } catch (e) {
      toast.erreur(e);
    }
  };

  const soumettreProjet = async () => {
    if (!(await enregistrerSiBesoin())) return;
    try {
      await soumettre.mutateAsync();
      setConfirmerSoumission(false);
      toast.notifier(
        'Projet soumis au siège : il est notifié par email et le reprendra pour établir l’attestation définitive.',
        'success',
      );
    } catch (e) {
      toast.erreur(e);
    }
  };

  const envoyerCorrection = async () => {
    if (correction === null) return;
    try {
      await demanderCorrection.mutateAsync(correction);
      setCorrection(null);
      toast.notifier('Projet renvoyé au distributeur pour correction : il est notifié.', 'success');
    } catch (e) {
      toast.erreur(e);
    }
  };

  const validerDefinitive = async (forcer = false) => {
    if (!(await enregistrerSiBesoin())) return;
    try {
      const res = await valider.mutateAsync(forcer ? { forcer: true, justification } : {});
      setForcage(false);
      toast.notifier(
        `Attestation définitive ${res.numero} validée : le distributeur est notifié.`,
        'success',
      );
    } catch (e) {
      toast.erreur(e);
    }
  };

  /** Sélectionne la première occurrence d'un extrait dans l'éditeur et y fait défiler. */
  const allerA = (extrait: string | null) => {
    if (!editor || !extrait) return;
    let cible: number | null = null;
    editor.state.doc.descendants((node, pos) => {
      if (cible !== null || !node.isText || !node.text) return;
      const idx = node.text.toLowerCase().indexOf(extrait.toLowerCase());
      if (idx >= 0) cible = pos + idx;
    });
    if (cible === null) return;
    editor.view.dispatch(
      editor.state.tr
        .setSelection(TextSelection.create(editor.state.doc, cible, cible + extrait.length))
        .scrollIntoView(),
    );
    editor.view.focus();
  };

  if (isLoading || (attestation === null && !gabarit))
    return <Spinner label="Chargement de l'attestation…" />;

  // Siège sur le projet : rien à instruire tant que le distributeur n'a pas soumis ; la définitive s'établit
  // à partir du projet soumis, elle n'est donc pas accessible avant.
  if (kind === 'projet' && estSiege && (!attestation || statut === 'EN_EDITION')) {
    return (
      <Card titre="✏️ Projet d'attestation">
        <Alert type="info">
          {attestation
            ? 'Le distributeur prépare son projet d’attestation : il ne vous a pas encore été soumis.'
            : 'Le distributeur n’a pas encore soumis de projet d’attestation.'}{' '}
          L’attestation définitive pourra être établie à partir de ce projet dès sa soumission.
        </Alert>
      </Card>
    );
  }

  const analyseAJour = Boolean(attestation?.analyse_a_jour) && !modifie;
  const titre = kind === 'projet' ? "Projet d'attestation" : 'Attestation définitive';
  const couleurStatut = validee ? 'green' : soumise ? 'orange' : aCorriger ? 'red' : 'blue';

  return (
    <div className="grid-2" style={{ gridTemplateColumns: 'minmax(0, 2fr) minmax(280px, 1fr)' }}>
      <Card
        titre={
          <div className="flex flex-wrap">
            <h2 style={{ margin: 0 }}>✏️ {titre}</h2>
            {attestation && statut && (
              <Badge couleur={couleurStatut}>
                {validee && attestation.numero
                  ? `Validée – ${attestation.numero}`
                  : LIBELLES_STATUT_ATTESTATION[statut]}
              </Badge>
            )}
            {!attestation && gabarit && (
              <Badge couleur="gray">
                {gabarit.source === 'PROJET'
                  ? `Pré-remplie depuis le projet soumis le ${formatDateHeure(gabarit.projet_soumis_le)}`
                  : 'Gabarit AXA pré-rempli'}
              </Badge>
            )}
          </div>
        }
      >
        {/* --- Bandeaux d'état --- */}
        {validee && attestation && (
          <Alert type="success">
            Validée le {formatDateHeure(attestation.validated_at)} par {attestation.validated_by}.
            {attestation.justification_forcage && (
              <div className="small">Validation forcée : {attestation.justification_forcage}</div>
            )}
          </Alert>
        )}
        {kind === 'projet' && soumise && attestation && (
          <Alert type={estSiege ? 'warning' : 'info'}>
            <strong>Projet soumis au siège le {formatDateHeure(attestation.soumise_le)}</strong>
            {estSiege
              ? ` par ${demande.distributeur.nom_affichage}. Reprenez-le pour établir l'attestation définitive (vous pourrez le rectifier), ou renvoyez-le au distributeur avec vos remarques.`
              : ' : en attente de traitement. Vous pouvez le reprendre pour le modifier tant que le siège ne l’a pas exploité.'}
          </Alert>
        )}
        {kind === 'projet' && aCorriger && attestation && (
          <Alert type="danger">
            <strong>Correction demandée par le siège :</strong> {attestation.commentaire_siege}
            {!estSiege && <div className="small">Corrigez le projet puis soumettez-le à nouveau.</div>}
          </Alert>
        )}
        {kind === 'projet' && definitiveEtablie && !estSiege && (
          <Alert type="info">
            L'attestation définitive est établie : le projet est figé et conservé à titre de brouillon.
          </Alert>
        )}
        {kind === 'projet' && !attestation && !estSiege && peutEditer && (
          <Alert type="info">
            Gabarit AXA pré-rempli depuis le FDR : complétez le projet puis{' '}
            <strong>soumettez-le au siège</strong>, qui établira l'attestation définitive.
          </Alert>
        )}
        {!validee && peutEditer && (
          <Alert type="info">
            <strong>Format officiel AXA.</strong> Le document reprend la structure de l'attestation
            d'assurance chantier AXA France (garanties, activités garanties, tableau de garanties, signature).
            Les zones dynamiques sont alimentées par le FDR ; le siège rectifie si besoin les montants du
            tableau de garanties, la liste des activités et la période de validité avant validation.
          </Alert>
        )}
        {kind === 'definitive' && !validee && estSiege && !peutEditer && (
          <Alert type="info">
            L'attestation définitive s'établit à partir du projet soumis par le distributeur, pour une demande
            acceptée.
          </Alert>
        )}

        {afficherPdf ? (
          pdfEnregistre ? (
            <iframe title="Attestation (PDF)" className="pdf-lecture" src={pdfEnregistre} />
          ) : (
            <Spinner label="Chargement du document…" />
          )
        ) : (
          <AttestationEditor
            contenuInitial={contenuInitial}
            assureur={gabarit?.assureur}
            entete={gabarit?.entete}
            cssDocument={gabarit?.css_document}
            estProjet={kind === 'projet'}
            variables={variables}
            libellesVariables={libelles}
            lectureSeule={lectureSeule}
            incoherences={incoherences}
            onEditor={onEditor}
          />
        )}

        {/* --- Actions --- */}
        <div className="actions mt-2">
          {!lectureSeule && (
            <Button onClick={() => sauvegarder()} chargement={enregistrer.isPending}>
              💾 Sauvegarder
            </Button>
          )}
          {!afficherPdf && (
            <Button variante="secondary" onClick={ouvrirApercu} chargement={previsualiser.isPending}>
              👁️ Prévisualiser
            </Button>
          )}
          {(kind === 'projet' || validee) && (
            <Button variante="secondary" onClick={exporterPdf}>
              {kind === 'definitive' ? "📄 Télécharger l'attestation" : '📄 Export PDF'}
            </Button>
          )}
          <span className="right" />

          {/* Distributeur – projet */}
          {kind === 'projet' && !lectureSeule && (
            <Button
              variante="success"
              onClick={() => setConfirmerSoumission(true)}
              chargement={soumettre.isPending}
            >
              📤 Soumettre au siège
            </Button>
          )}
          {kind === 'projet' && peutEditer && soumise && !estSiege && (
            <Button
              variante="secondary"
              onClick={() => rouvrir.mutate(undefined, { onError: (e) => toast.erreur(e) })}
              chargement={rouvrir.isPending}
            >
              ↩ Reprendre le projet
            </Button>
          )}

          {/* Siège – projet soumis */}
          {kind === 'projet' && estSiege && soumise && !definitiveEtablie && (
            <>
              <Button variante="secondary" onClick={() => setCorrection('')}>
                ✏️ Demander une correction
              </Button>
              {onEtablirDefinitive && (
                <Button variante="success" onClick={onEtablirDefinitive}>
                  ✅ Établir l'attestation définitive à partir de ce projet
                </Button>
              )}
            </>
          )}

          {/* Siège – définitive */}
          {kind === 'definitive' && !lectureSeule && (
            <Button
              variante="success"
              onClick={() => validerDefinitive(false)}
              chargement={valider.isPending}
            >
              ✅ Valider l'attestation
            </Button>
          )}
          {kind === 'definitive' && peutEditer && !validee && (
            <Button variante="ghost" onClick={() => setForcage(true)}>
              Forcer la validation…
            </Button>
          )}
        </div>
      </Card>

      <div>
        {!lectureSeule && (
          <Card titre="🧩 Zones dynamiques" className="mb-2">
            <p className="small muted">
              Insérez une donnée du FDR à la position du curseur. Les zones sont non modifiables et se mettent
              à jour avec le FDR.
            </p>
            <div className="variables-panel">
              {Object.entries(libelles).map(([cle, libelle]) => (
                <button
                  key={cle}
                  type="button"
                  onClick={() => editor?.chain().focus().insererVariable(cle).run()}
                  disabled={!editor}
                  title={variables[cle] ?? ''}
                >
                  {libelle}
                </button>
              ))}
            </div>
          </Card>
        )}
        {analyseDisponible && (
          <Card
            titre="🤖 Analyse de cohérence (IA simulée)"
            variante={analyse ? (analyse.statut === 'COHERENT' ? 'success' : 'danger') : 'default'}
          >
            <p className="small muted">
              Compare l'attestation au FDR : identité de l'assuré, contrat, chantier, dates, montants,
              travaux, garanties et mentions obligatoires.
            </p>
            <Button
              onClick={lancerAnalyse}
              chargement={analyser.isPending}
              disabled={!attestation && lectureSeule}
              style={{ width: '100%' }}
            >
              {analyser.isPending ? 'Analyse en cours…' : '🤖 Analyser avec IA'}
            </Button>
            {analyse && (
              <div className="mt-2">
                <AnalysePanel analyse={analyse} aJour={analyseAJour} onCliquer={allerA} />
              </div>
            )}
          </Card>
        )}
        {kind === 'projet' && !estSiege && (
          <Card titre="ℹ️ Circuit de l'attestation" variante="plain">
            <ol className="small" style={{ paddingLeft: '1.2rem', margin: 0 }}>
              <li>Vous préparez le projet à partir du gabarit AXA pré-rempli.</li>
              <li>
                Vous le <strong>soumettez au siège</strong> (notification + email).
              </li>
              <li>
                Le siège le valide ou le rectifie pour établir l'attestation définitive, ou vous le renvoie
                pour correction.
              </li>
              <li>Vous êtes notifié dès que l'attestation définitive est disponible au téléchargement.</li>
            </ol>
          </Card>
        )}
      </div>

      <Modal
        ouvert={apercu !== null}
        titre="Prévisualisation de l'attestation"
        onFermer={() => setApercu(null)}
        large
      >
        {apercu && <iframe title="Aperçu de l'attestation (PDF)" className="preview-frame" src={apercu} />}
      </Modal>

      <Modal
        ouvert={confirmerSoumission}
        titre="Soumettre le projet au siège"
        onFermer={() => setConfirmerSoumission(false)}
        pied={
          <>
            <Button variante="secondary" onClick={() => setConfirmerSoumission(false)}>
              Annuler
            </Button>
            <Button variante="success" chargement={soumettre.isPending} onClick={soumettreProjet}>
              Confirmer la soumission
            </Button>
          </>
        }
      >
        <p>
          Le projet sera enregistré puis transmis au siège, qui en sera notifié par email. Il ne sera plus
          modifiable tant que vous ne l'aurez pas repris ou que le siège ne l'aura pas renvoyé pour
          correction.
        </p>
      </Modal>

      <Modal
        ouvert={correction !== null}
        titre="Demander une correction du projet"
        onFermer={() => setCorrection(null)}
        pied={
          <>
            <Button variante="secondary" onClick={() => setCorrection(null)}>
              Annuler
            </Button>
            <Button
              variante="danger"
              disabled={(correction ?? '').trim().length < 10}
              chargement={demanderCorrection.isPending}
              onClick={envoyerCorrection}
            >
              Renvoyer au distributeur
            </Button>
          </>
        }
      >
        <p>
          Indiquez au distributeur les corrections attendues (10 caractères minimum). Il sera notifié et
          pourra resoumettre le projet.
        </p>
        <Textarea
          value={correction ?? ''}
          onChange={(e) => setCorrection(e.target.value)}
          placeholder="Corrections attendues…"
          autoFocus
        />
      </Modal>

      <Modal
        ouvert={forcage}
        titre="Forcer la validation"
        onFermer={() => setForcage(false)}
        pied={
          <>
            <Button variante="secondary" onClick={() => setForcage(false)}>
              Annuler
            </Button>
            <Button
              variante="danger"
              disabled={justification.trim().length < 10}
              chargement={valider.isPending}
              onClick={() => validerDefinitive(true)}
            >
              Valider malgré l'analyse
            </Button>
          </>
        }
      >
        <Alert type="warning">
          La validation sans analyse cohérente doit être justifiée (10 caractères minimum). La justification
          est consignée dans l'historique de la demande.
        </Alert>
        <Textarea
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          placeholder="Justification…"
          autoFocus
        />
      </Modal>
    </div>
  );
}

// Libellés de repli (identiques à VARIABLES_DISPONIBLES côté backend) en attendant le gabarit.
const VARIABLES_PAR_DEFAUT: Record<string, string> = {
  assure_nom: "Nom / raison sociale de l'assuré",
  assure_adresse: "Adresse de l'assuré",
  assure_cp_ville: "Code postal et ville de l'assuré",
  assure_ville: "Ville de l'assuré",
  assure_siret: "SIRET de l'assuré",
  numero_contrat: 'Numéro de contrat',
  reference_client: 'Référence client',
  produit: "Produit d'assurance (contrat)",
  contrat_periode_debut: 'Début de la période de validité du contrat',
  contrat_periode_fin: 'Fin de la période de validité du contrat',
  plafond_cout: 'Plafond du coût total de construction',
  chantier_nom: 'Nom du chantier',
  chantier_ville: 'Ville du chantier',
  type_chantier: 'Nature du chantier',
  usage: "Destination de l'ouvrage",
  date_debut: 'Date de début du chantier',
  date_fin: 'Date de fin du chantier',
  cout_total: 'Coût total du chantier',
  montant_prestation: 'Montant de la prestation',
  type_intervention: "Type d'intervention",
  description_travaux: 'Description des travaux',
  activites_garanties: 'Mention sur les activités garanties',
  distributeur_nom: 'Distributeur émetteur',
  numero_attestation: "Numéro d'attestation",
  date_courrier: 'Date du courrier',
  date_edition: "Date d'édition (en toutes lettres)",
  lieu_signature: 'Lieu de signature',
  signataire_nom: 'Signataire',
  signataire_titre: 'Titre du signataire',
};
