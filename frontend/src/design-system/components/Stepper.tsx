export interface Etape {
  cle: string;
  libelle: string;
  termine?: boolean;
  desactive?: boolean;
}

export function Stepper({
  etapes,
  courante,
  onChange,
}: {
  etapes: Etape[];
  courante: string;
  onChange: (cle: string) => void;
}) {
  return (
    <nav className="stepper" aria-label="Étapes de la demande">
      {etapes.map((e, i) => (
        <button
          key={e.cle}
          type="button"
          className={`stepper__step ${e.termine ? 'stepper__step--done' : ''}`}
          aria-current={courante === e.cle ? 'step' : undefined}
          disabled={e.desactive}
          onClick={() => onChange(e.cle)}
        >
          <span className="stepper__num" aria-hidden>
            {e.termine ? '✓' : i + 1}
          </span>
          {e.libelle}
        </button>
      ))}
    </nav>
  );
}
