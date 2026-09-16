import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react';
import { forwardRef, useId } from 'react';

interface FieldProps {
  label: ReactNode;
  requis?: boolean;
  aide?: ReactNode;
  erreur?: string;
  children: (id: string, describedBy: string | undefined) => ReactNode;
}

/** Enveloppe libellé + aide + erreur ; fournit l'`id` au contrôle enfant pour l'accessibilité. */
export function Field({ label, requis, aide, erreur, children }: FieldProps) {
  const id = useId();
  const describedBy = erreur ? `${id}-err` : aide ? `${id}-help` : undefined;
  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        {label}
        {requis && (
          <span className="req" aria-hidden>
            *
          </span>
        )}
      </label>
      {children(id, describedBy)}
      {aide && !erreur && (
        <span id={`${id}-help`} className="field__help">
          {aide}
        </span>
      )}
      {erreur && (
        <span id={`${id}-err`} className="field__error" role="alert">
          {erreur}
        </span>
      )}
    </div>
  );
}

type InputProps = InputHTMLAttributes<HTMLInputElement> & { invalide?: boolean };
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { invalide, className = '', ...rest },
  ref,
) {
  return <input ref={ref} className={`input ${className}`} aria-invalid={invalide || undefined} {...rest} />;
});

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & { invalide?: boolean };
export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { invalide, className = '', ...rest },
  ref,
) {
  return (
    <select ref={ref} className={`select ${className}`} aria-invalid={invalide || undefined} {...rest} />
  );
});

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & { invalide?: boolean };
export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { invalide, className = '', ...rest },
  ref,
) {
  return (
    <textarea ref={ref} className={`textarea ${className}`} aria-invalid={invalide || undefined} {...rest} />
  );
});

interface SegmentedProps<T extends string> {
  name: string;
  valeur: T | null | undefined;
  options: { valeur: T; libelle: string }[];
  onChange: (valeur: T) => void;
  disabled?: boolean;
  invalide?: boolean;
  id?: string;
}

/** Groupe de boutons radio « segmenté » (Oui / Non, types…). */
export function Segmented<T extends string>({
  name,
  valeur,
  options,
  onChange,
  disabled,
  invalide,
  id,
}: SegmentedProps<T>) {
  return (
    <div className={`segmented ${invalide ? 'segmented--invalid' : ''}`} role="radiogroup" id={id}>
      {options.map((o) => (
        <label key={o.valeur}>
          <input
            type="radio"
            name={name}
            value={o.valeur}
            checked={valeur === o.valeur}
            onChange={() => onChange(o.valeur)}
            disabled={disabled}
          />
          {o.libelle}
        </label>
      ))}
    </div>
  );
}

export function OuiNon({
  name,
  valeur,
  onChange,
  disabled,
  invalide,
  id,
}: {
  name: string;
  valeur: boolean | null | undefined;
  onChange: (v: boolean) => void;
  disabled?: boolean;
  invalide?: boolean;
  id?: string;
}) {
  return (
    <Segmented<'oui' | 'non'>
      id={id}
      name={name}
      valeur={valeur === true ? 'oui' : valeur === false ? 'non' : null}
      options={[
        { valeur: 'oui', libelle: 'Oui' },
        { valeur: 'non', libelle: 'Non' },
      ]}
      onChange={(v) => onChange(v === 'oui')}
      disabled={disabled}
      invalide={invalide}
    />
  );
}
