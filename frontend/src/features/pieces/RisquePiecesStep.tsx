// Écran 3 : évaluation automatique du risque + pièces justificatives (upload, liste, suppression),
// indicateur dossier complet / incomplet et synthèse.
import { useRef, useState, type DragEvent } from 'react';
import { useCompletude, useReferentiels, useScoring } from '@/api/demandes';
import { useChangerTypePiece, usePieces, useSupprimerPiece, useUploaderPiece } from '@/api/pieces';
import { telechargerFichier } from '@/api/client';
import type { DemandeDetail } from '@/api/types';
import { formatDateHeure, formatTaille } from '@/lib/format';
import { Alert, Badge, Button, Card, Gauge, Select, Spinner, useToast } from '@/design-system/components';

export function RisquePiecesStep({ demande, lectureSeule }: { demande: DemandeDetail; lectureSeule: boolean }) {
  const { data: scoring } = useScoring(demande.id);
  const { data: completude } = useCompletude(demande.id);
  const { data: pieces } = usePieces(demande.id);
  const { data: referentiels } = useReferentiels();
  const uploader = useUploaderPiece(demande.id);
  const supprimer = useSupprimerPiece(demande.id);
  const changerType = useChangerTypePiece(demande.id);
  const toast = useToast();
  const [typeChoisi, setTypeChoisi] = useState('');
  const [actif, setActif] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const deposer = async (fichiers: FileList | File[]) => {
    if (!typeChoisi) {
      toast.notifier('Choisissez d’abord le type de pièce.', 'error');
      return;
    }
    for (const fichier of Array.from(fichiers)) {
      try {
        const piece = await uploader.mutateAsync({ fichier, typePiece: typeChoisi });
        toast.notifier(`« ${fichier.name} » déposé et enregistré sous « ${piece.nom_fichier} ».`, 'success');
      } catch (e) {
        toast.erreur(e);
      }
    }
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setActif(false);
    if (!lectureSeule) void deposer(e.dataTransfer.files);
  };

  const telecharger = (id: string, nom: string) =>
    telechargerFichier(`/demandes/${demande.id}/pieces/${id}/download/`, nom).catch((e) => toast.erreur(e));

  return (
    <div className="grid-2">
      <Card titre="📊 Évaluation automatique du risque">
        {!scoring ? (
          <Spinner />
        ) : (
          <>
            <Gauge score={scoring.score} niveau={scoring.niveau} />
            <p className="mt-2">{scoring.synthese}</p>
            <table className="table">
              <thead>
                <tr><th>Indicateur</th><th>Détail</th><th className="num">Points</th></tr>
              </thead>
              <tbody>
                {scoring.indicateurs.map((i) => (
                  <tr key={i.code}>
                    <td><strong>{i.libelle}</strong></td>
                    <td className="small">{i.detail}</td>
                    <td className="num">{i.points > 0 ? `+${i.points}` : '0'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="small muted mt-1">Indicateurs simulés à titre indicatif : le siège reste seul décisionnaire.</p>
          </>
        )}
      </Card>

      <div>
        <Card titre="📂 Pièces justificatives" variante={completude?.complet ? 'success' : 'danger'}>
          {completude && (
            <Alert type={completude.complet ? 'success' : 'warning'}>
              {completude.complet ? (
                <strong>Dossier complet ✅</strong>
              ) : (
                <>
                  <strong>Dossier incomplet ❌</strong> — {completude.manquants.length} pièce(s) requise(s) manquante(s).
                </>
              )}
            </Alert>
          )}
          {completude && completude.exigences.length === 0 && <p className="muted">Aucune pièce requise pour ce dossier. Vous pouvez néanmoins joindre tout document utile.</p>}
          {completude && completude.exigences.length > 0 && (
            <ul className="checklist">
              {completude.exigences.map((e) => (
                <li key={e.code}>
                  <span className={`checklist__icon ${e.satisfait ? 'checklist__icon--ok' : e.niveau === 'REQUIS' ? 'checklist__icon--ko' : 'checklist__icon--reco'}`} aria-hidden>
                    {e.satisfait ? '✓' : e.niveau === 'REQUIS' ? '!' : '?'}
                  </span>
                  <div className="grow">
                    <div className="flex between">
                      <strong>{e.libelle}</strong>
                      <Badge couleur={e.satisfait ? 'green' : e.niveau === 'REQUIS' ? 'red' : 'orange'}>
                        {e.satisfait ? 'Fournie' : e.niveau === 'REQUIS' ? 'Manquante' : 'Recommandée'}
                      </Badge>
                    </div>
                    <div className="small muted">{e.raison}</div>
                  </div>
                </li>
              ))}
            </ul>
          )}

          {!lectureSeule && (
            <div className="mt-2">
              <div className="flex" style={{ marginBottom: '0.5rem' }}>
                <label className="field__label" htmlFor="type-piece">Type de pièce</label>
                <Select id="type-piece" value={typeChoisi} onChange={(e) => setTypeChoisi(e.target.value)} style={{ width: 'auto', flex: 1 }}>
                  <option value="">— Choisir le type de la pièce à déposer —</option>
                  {referentiels?.types_pieces.map((t) => (
                    <option key={t.code} value={t.code}>{t.libelle}</option>
                  ))}
                </Select>
              </div>
              <div
                className={`dropzone ${actif ? 'dropzone--active' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setActif(true); }}
                onDragLeave={() => setActif(false)}
                onDrop={onDrop}
                onClick={() => inputRef.current?.click()}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
              >
                <input ref={inputRef} type="file" multiple accept={referentiels?.upload.extensions.join(',')} onChange={(e) => e.target.files && deposer(e.target.files)} />
                {uploader.isPending ? <Spinner label="Envoi en cours…" /> : (
                  <>
                    <strong>Glissez vos fichiers ici</strong> ou cliquez pour parcourir
                    <div className="small muted">
                      {referentiels?.upload.extensions.join(', ')} · {formatTaille(referentiels?.upload.max_bytes ?? 0)} max par fichier
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </Card>

        <Card titre="📄 Fichiers déposés" className="mt-2">
          {!pieces ? <Spinner /> : pieces.length === 0 ? <p className="muted">Aucun fichier.</p> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Fichier</th><th>Type</th><th>Taille</th><th>Déposé</th><th></th></tr></thead>
                <tbody>
                  {pieces.map((p) => (
                    <tr key={p.id}>
                      <td>
                        <button type="button" className="btn btn--ghost btn--sm" onClick={() => telecharger(p.id, p.nom_fichier)}>
                          ⬇ {p.nom_fichier}
                        </button>
                        {p.nom_original !== p.nom_fichier && <div className="small muted">déposé sous « {p.nom_original} »</div>}
                      </td>
                      <td>
                        {lectureSeule ? p.libelle_type : (
                          <Select value={p.type_piece} onChange={(e) => changerType.mutate({ pieceId: p.id, typePiece: e.target.value })} style={{ minWidth: 220 }}>
                            {referentiels?.types_pieces.map((t) => <option key={t.code} value={t.code}>{t.libelle}</option>)}
                          </Select>
                        )}
                      </td>
                      <td className="num">{formatTaille(p.taille)}</td>
                      <td className="small">{formatDateHeure(p.created_at)}<div className="muted">{p.deposee_par}</div></td>
                      <td>
                        {!lectureSeule && (
                          <Button variante="ghost" taille="sm" onClick={() => supprimer.mutate(p.id, { onError: (e) => toast.erreur(e) })} aria-label={`Supprimer ${p.nom_original}`}>
                            🗑
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {completude && completude.pieces_hors_exigence.length > 0 && (
            <p className="small muted mt-1">
              {completude.pieces_hors_exigence.length} fichier(s) d'un type non requis (facultatifs) : ils sont conservés et transmis au siège.
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}
