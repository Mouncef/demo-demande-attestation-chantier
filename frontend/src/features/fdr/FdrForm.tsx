// Écran 2 : Formulaire de Déclaration du Risque – formulaire dynamique (sections conditionnelles),
// sauvegarde brouillon avec verrou optimiste, erreurs backend mappées champ par champ.
import { useEffect } from 'react';
import { Controller, useForm, useWatch } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useEnregistrerFdr, useInvaliderDemande } from '@/api/demandes';
import { erreurApi } from '@/api/client';
import type { DemandeDetail } from '@/api/types';
import { LIBELLES_INTERVENTION, LIBELLES_TYPE_CHANTIER, LIBELLES_USAGE } from '@/lib/libelles';
import {
  Alert,
  Button,
  Card,
  Field,
  Input,
  OuiNon,
  Segmented,
  Select,
  StepNav,
  Textarea,
  useToast,
} from '@/design-system/components';
import {
  depuisFdr,
  schemaFdr,
  schemaFdrEnvoi,
  versPayload,
  type FdrFormOutput,
  type FdrFormValues,
} from './schema';

interface Props {
  demande: DemandeDetail;
  lectureSeule: boolean;
  erreursEnvoi?: Record<string, string>;
  onEnregistre?: () => void;
  /** Navigation du parcours : « Suivant » valide l'ensemble des champs avant d'enregistrer et d'avancer. */
  onSuivant?: () => void | Promise<void>;
  onPrecedent?: () => void;
  /** Affiche immédiatement les erreurs bloquant l'envoi (ex. retour depuis « Validation & envoi »). */
  signalerErreurs?: boolean;
}

export function FdrForm({
  demande,
  lectureSeule,
  erreursEnvoi = {},
  onEnregistre,
  onSuivant,
  onPrecedent,
  signalerErreurs = false,
}: Props) {
  const toast = useToast();
  const enregistrer = useEnregistrerFdr(demande.id);
  const invalider = useInvaliderDemande();
  const form = useForm<FdrFormValues, unknown, FdrFormOutput>({
    resolver: zodResolver(schemaFdr),
    defaultValues: depuisFdr(demande.fdr as unknown as Record<string, unknown>),
    // Aucune validation à la saisie ni à la perte de focus : les erreurs n'apparaissent qu'au clic sur
    // « Valider et continuer » / « Enregistrer » et restent affichées telles quelles jusqu'au clic suivant,
    // qui revalide l'ensemble des champs (pas de revalidation partielle champ par champ).
    mode: 'onSubmit',
    reValidateMode: 'onSubmit',
  });
  const { register, control, handleSubmit, reset, setError, clearErrors, getValues, formState } = form;
  const { errors, isDirty } = formState;
  // Erreurs par champ affichées : celles de la validation client (au clic) ou de l'API (à l'enregistrement).
  // Les erreurs d'envoi calculées par le backend sur le FDR enregistré ne sont reprises que lorsque l'on
  // revient volontairement depuis « Validation & envoi » (`signalerErreurs`) : sinon elles refléteraient
  // un état antérieur et marqueraient des champs déjà corrigés.
  const montrerErreursBackend = signalerErreurs && !isDirty;

  // Resynchronisation lorsque la demande est rechargée (ex. après un conflit de version).
  useEffect(() => {
    reset(depuisFdr(demande.fdr as unknown as Record<string, unknown>));
  }, [demande.fdr, demande.version, reset]);

  const valeurs = useWatch({ control });

  /** Enregistre le FDR ; renvoie `true` en cas de succès (erreurs API mappées champ par champ sinon). */
  const sauvegarder = async (valides: FdrFormOutput): Promise<boolean> => {
    try {
      await enregistrer.mutateAsync({ ...versPayload(valides), version: demande.version });
      onEnregistre?.();
      return true;
    } catch (err) {
      const e = erreurApi(err);
      if (e.code === 'VALIDATION' && e.errors) {
        for (const [champ, messages] of Object.entries(e.errors)) {
          setError(champ as keyof FdrFormValues, {
            message: Array.isArray(messages) ? messages[0] : String(messages),
          });
        }
        toast.notifier('Certains champs sont invalides.', 'error');
      } else if (e.code === 'CONFLIT_VERSION') {
        toast.erreur(err);
        invalider(demande.id);
      } else toast.erreur(err);
      return false;
    }
  };

  /** Sauvegarde du brouillon : formats et règles croisées seulement, les champs peuvent rester vides. */
  const onSubmit = handleSubmit(async (valides) => {
    if (await sauvegarder(valides)) toast.notifier('Brouillon enregistré.', 'success');
  });

  /** Fait défiler jusqu'au premier champ en erreur. */
  const allerAuPremierChampInvalide = () =>
    setTimeout(
      () =>
        document
          .querySelector('[aria-invalid="true"], .segmented--invalid')
          ?.scrollIntoView({ behavior: 'smooth', block: 'center' }),
      50,
    );

  /** « Suivant » : validation complète (obligations + règles), enregistrement, puis étape suivante. */
  const suivant = async () => {
    if (lectureSeule) {
      onSuivant?.();
      return;
    }
    clearErrors();
    const resultat = schemaFdrEnvoi.safeParse(getValues());
    if (!resultat.success) {
      // Une seule erreur par champ (la première rencontrée) ; tous les champs sont réévalués.
      const signales = new Set<string>();
      for (const issue of resultat.error.issues) {
        const champ = issue.path[0] as keyof FdrFormValues | undefined;
        if (champ && !signales.has(champ)) {
          signales.add(champ);
          setError(champ, { message: issue.message });
        }
      }
      toast.notifier('Complétez les champs signalés avant de passer à l\u2019étape suivante.', 'error');
      allerAuPremierChampInvalide();
      return;
    }
    if (await sauvegarder(resultat.data)) await onSuivant?.();
    else allerAuPremierChampInvalide();
  };

  const err = (champ: keyof FdrFormValues) =>
    errors[champ]?.message ?? (montrerErreursBackend ? erreursEnvoi[champ] : undefined);
  const desactive = lectureSeule || enregistrer.isPending;

  return (
    <form onSubmit={onSubmit} noValidate>
      {lectureSeule && (
        <Alert type="info">Le FDR n'est plus modifiable dans le statut actuel de la demande.</Alert>
      )}
      {montrerErreursBackend && Object.keys(erreursEnvoi).length > 0 && (
        <Alert type="warning">
          Des informations sont manquantes ou invalides pour l'envoi au siège : les champs concernés sont
          signalés ci-dessous.
        </Alert>
      )}

      <div className="grid-2">
        <Card titre="🧑 L'assuré">
          <Field label="Nom / raison sociale" requis erreur={err('assure_nom')}>
            {(id) => (
              <Input
                id={id}
                {...register('assure_nom')}
                disabled={desactive}
                invalide={Boolean(err('assure_nom'))}
              />
            )}
          </Field>
          <Field label="Adresse" requis erreur={err('assure_adresse')}>
            {(id) => (
              <Input
                id={id}
                {...register('assure_adresse')}
                disabled={desactive}
                invalide={Boolean(err('assure_adresse'))}
              />
            )}
          </Field>
          <div className="grid-2">
            <Field label="Code postal" requis erreur={err('assure_code_postal')}>
              {(id) => (
                <Input
                  id={id}
                  inputMode="numeric"
                  maxLength={5}
                  {...register('assure_code_postal')}
                  disabled={desactive}
                  invalide={Boolean(err('assure_code_postal'))}
                />
              )}
            </Field>
            <Field label="Ville" requis erreur={err('assure_ville')}>
              {(id) => (
                <Input
                  id={id}
                  {...register('assure_ville')}
                  disabled={desactive}
                  invalide={Boolean(err('assure_ville'))}
                />
              )}
            </Field>
          </div>
          <Field
            label="SIRET"
            requis
            erreur={err('assure_siret')}
            aide="14 chiffres (imprimé sur l'attestation)"
          >
            {(id) => (
              <Input
                id={id}
                inputMode="numeric"
                {...register('assure_siret')}
                disabled={desactive}
                invalide={Boolean(err('assure_siret'))}
              />
            )}
          </Field>
          <Field
            label="Numéro de contrat"
            requis
            erreur={err('numero_contrat')}
            aide="6 à 20 caractères alphanumériques (ex. RCD2026LY0142)"
          >
            {(id) => (
              <Input
                id={id}
                {...register('numero_contrat')}
                disabled={desactive}
                invalide={Boolean(err('numero_contrat'))}
                style={{ textTransform: 'uppercase' }}
              />
            )}
          </Field>
          <Field
            label="Référence client"
            erreur={err('reference_client')}
            aide="Facultatif – reprise dans « Vos références » sur l'attestation"
          >
            {(id) => <Input id={id} {...register('reference_client')} disabled={desactive} />}
          </Field>
        </Card>

        <Card titre="🏗️ Le chantier">
          <Field label="Nom du chantier" requis erreur={err('chantier_nom')}>
            {(id) => (
              <Input
                id={id}
                {...register('chantier_nom')}
                disabled={desactive}
                invalide={Boolean(err('chantier_nom'))}
              />
            )}
          </Field>
          <Field label="Ville" requis erreur={err('chantier_ville')}>
            {(id) => (
              <Input
                id={id}
                {...register('chantier_ville')}
                disabled={desactive}
                invalide={Boolean(err('chantier_ville'))}
              />
            )}
          </Field>
          <Field label="Type de chantier" requis erreur={err('type_chantier')}>
            {(id) => (
              <Controller
                control={control}
                name="type_chantier"
                render={({ field }) => (
                  <Segmented
                    id={id}
                    name="type_chantier"
                    valeur={field.value}
                    onChange={field.onChange}
                    disabled={desactive}
                    invalide={Boolean(err('type_chantier'))}
                    options={Object.entries(LIBELLES_TYPE_CHANTIER).map(([valeur, libelle]) => ({
                      valeur: valeur as 'CONSTRUCTION_NEUVE' | 'RENOVATION',
                      libelle,
                    }))}
                  />
                )}
              />
            )}
          </Field>
          {valeurs.type_chantier === 'RENOVATION' && (
            <Field
              label="Modification de la structure ?"
              requis
              erreur={err('modification_structure')}
              aide="Si oui, une étude structure et l'autorisation d'urbanisme seront requises."
            >
              {(id) => (
                <Controller
                  control={control}
                  name="modification_structure"
                  render={({ field }) => (
                    <OuiNon
                      id={id}
                      name="modification_structure"
                      valeur={field.value}
                      onChange={field.onChange}
                      disabled={desactive}
                      invalide={Boolean(err('modification_structure'))}
                    />
                  )}
                />
              )}
            </Field>
          )}
        </Card>

        <Card titre="🏢 Usage et complexité">
          <Field label="Usage de l'ouvrage" requis erreur={err('usage')}>
            {(id) => (
              <Select id={id} {...register('usage')} disabled={desactive} invalide={Boolean(err('usage'))}>
                <option value="">— Sélectionner —</option>
                {Object.entries(LIBELLES_USAGE).map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          {valeurs.usage === 'AUTRE' && (
            <Field label="Précisez l'usage" requis erreur={err('usage_autre_precision')}>
              {(id) => (
                <Input
                  id={id}
                  {...register('usage_autre_precision')}
                  disabled={desactive}
                  invalide={Boolean(err('usage_autre_precision'))}
                />
              )}
            </Field>
          )}
          <Field
            label="Chantier atypique ?"
            requis
            erreur={err('chantier_atypique')}
            aide="Ouvrage inhabituel, techniques particulières, site contraint… Si oui, descriptif technique et photos/plans requis."
          >
            {(id) => (
              <Controller
                control={control}
                name="chantier_atypique"
                render={({ field }) => (
                  <OuiNon
                    id={id}
                    name="chantier_atypique"
                    valeur={field.value}
                    onChange={field.onChange}
                    disabled={desactive}
                    invalide={Boolean(err('chantier_atypique'))}
                  />
                )}
              />
            )}
          </Field>
        </Card>

        <Card titre="📅 Dates et montant global">
          <div className="grid-2">
            <Field label="Date de début" requis erreur={err('date_debut')}>
              {(id) => (
                <Input
                  id={id}
                  type="date"
                  {...register('date_debut')}
                  disabled={desactive}
                  invalide={Boolean(err('date_debut'))}
                />
              )}
            </Field>
            <Field label="Date de fin" requis erreur={err('date_fin')}>
              {(id) => (
                <Input
                  id={id}
                  type="date"
                  {...register('date_fin')}
                  disabled={desactive}
                  invalide={Boolean(err('date_fin'))}
                />
              )}
            </Field>
          </div>
          <Field
            label="Coût total du chantier (€ HT)"
            requis
            erreur={err('cout_total')}
            aide="Au-delà de 10 M€, marché signé, attestation DO et planning sont requis."
          >
            {(id) => (
              <Input
                id={id}
                inputMode="decimal"
                className="input--montant"
                placeholder="0,00"
                {...register('cout_total')}
                disabled={desactive}
                invalide={Boolean(err('cout_total'))}
              />
            )}
          </Field>
        </Card>

        <Card titre="🧾 L'intervention" className="grid-span">
          <Field
            label="Description des travaux"
            requis
            erreur={err('description_travaux')}
            aide="Nature précise des travaux réalisés par l'assuré (20 caractères minimum)."
          >
            {(id) => (
              <Textarea
                id={id}
                {...register('description_travaux')}
                disabled={desactive}
                invalide={Boolean(err('description_travaux'))}
              />
            )}
          </Field>
          <Field label="Montant de la prestation (€ HT)" requis erreur={err('montant_prestation')}>
            {(id) => (
              <Input
                id={id}
                inputMode="decimal"
                className="input--montant"
                placeholder="0,00"
                {...register('montant_prestation')}
                disabled={desactive}
                invalide={Boolean(err('montant_prestation'))}
              />
            )}
          </Field>
          <Field label="Type d'intervention" requis erreur={err('type_intervention')}>
            {(id) => (
              <Controller
                control={control}
                name="type_intervention"
                render={({ field }) => (
                  <Segmented
                    id={id}
                    name="type_intervention"
                    valeur={field.value}
                    onChange={field.onChange}
                    disabled={desactive}
                    invalide={Boolean(err('type_intervention'))}
                    options={Object.entries(LIBELLES_INTERVENTION).map(([valeur, libelle]) => ({
                      valeur: valeur as 'ENTREPRISE_PRINCIPALE' | 'SOUS_TRAITANT',
                      libelle,
                    }))}
                  />
                )}
              />
            )}
          </Field>
          {valeurs.type_intervention === 'SOUS_TRAITANT' && (
            <Field
              label="Entreprise principale (donneur d'ordre)"
              erreur={err('entreprise_principale_nom')}
              aide="Recommandé : le contrat de sous-traitance pourra être joint."
            >
              {(id) => <Input id={id} {...register('entreprise_principale_nom')} disabled={desactive} />}
            </Field>
          )}
        </Card>

        <Card titre="❓ Questions">
          <Field
            label="L'activité est-elle couverte par le contrat ?"
            requis
            erreur={err('activite_couverte')}
          >
            {(id) => (
              <Controller
                control={control}
                name="activite_couverte"
                render={({ field }) => (
                  <OuiNon
                    id={id}
                    name="activite_couverte"
                    valeur={field.value}
                    onChange={field.onChange}
                    disabled={desactive}
                    invalide={Boolean(err('activite_couverte'))}
                  />
                )}
              />
            )}
          </Field>
          {valeurs.activite_couverte === false && (
            <Field
              label="Précisez l'activité non couverte"
              requis
              erreur={err('activite_non_couverte_precision')}
              aide="Un descriptif de l'activité et un justificatif de qualification seront requis."
            >
              {(id) => (
                <Textarea
                  id={id}
                  {...register('activite_non_couverte_precision')}
                  disabled={desactive}
                  invalide={Boolean(err('activite_non_couverte_precision'))}
                />
              )}
            </Field>
          )}
          <Field
            label="S'agit-il de travaux standards ?"
            requis
            erreur={err('travaux_standards')}
            aide="Techniques traditionnelles (DTU). Si non, un avis technique sera requis."
          >
            {(id) => (
              <Controller
                control={control}
                name="travaux_standards"
                render={({ field }) => (
                  <OuiNon
                    id={id}
                    name="travaux_standards"
                    valeur={field.value}
                    onChange={field.onChange}
                    disabled={desactive}
                    invalide={Boolean(err('travaux_standards'))}
                  />
                )}
              />
            )}
          </Field>
        </Card>
      </div>

      {/* Barre d'actions unique : Précédent | (état) Enregistrer le brouillon · Valider et continuer */}
      <StepNav
        onPrecedent={onPrecedent}
        onSuivant={onSuivant ? suivant : undefined}
        libelleSuivant={lectureSeule ? 'Suivant' : 'Valider et continuer'}
        chargement={enregistrer.isPending}
        actions={
          !lectureSeule && (
            <>
              {isDirty && <span className="muted small">Modifications non enregistrées</span>}
              <Button type="submit" variante="secondary" chargement={enregistrer.isPending}>
                💾 Enregistrer le brouillon
              </Button>
            </>
          )
        }
      />
    </form>
  );
}
