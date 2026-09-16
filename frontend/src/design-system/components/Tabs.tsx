export function Tabs({
  onglets,
  actif,
  onChange,
}: {
  onglets: { cle: string; libelle: string }[];
  actif: string;
  onChange: (c: string) => void;
}) {
  return (
    <div className="tabs" role="tablist">
      {onglets.map((o) => (
        <button
          key={o.cle}
          type="button"
          role="tab"
          aria-selected={actif === o.cle}
          onClick={() => onChange(o.cle)}
        >
          {o.libelle}
        </button>
      ))}
    </div>
  );
}
