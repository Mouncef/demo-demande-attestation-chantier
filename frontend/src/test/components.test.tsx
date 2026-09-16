import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BadgeStatut, Gauge, OuiNon, Stepper } from '@/design-system/components';

describe('composants du design system', () => {
  it('affiche le libellé du statut', () => {
    render(<BadgeStatut statut="A_COMPLETER" />);
    expect(screen.getByText('Compléments demandés')).toBeInTheDocument();
  });

  it('la jauge expose le score et le niveau', () => {
    render(<Gauge score={72} niveau="ELEVE" />);
    expect(screen.getByRole('meter')).toHaveAttribute('aria-valuenow', '72');
    expect(screen.getByText('Risque Élevé')).toBeInTheDocument();
  });

  it('OuiNon renvoie un booléen', async () => {
    const onChange = vi.fn();
    render(<OuiNon name="q" valeur={null} onChange={onChange} />);
    await userEvent.click(screen.getByLabelText('Non'));
    expect(onChange).toHaveBeenCalledWith(false);
  });

  it('le stepper signale l’étape courante', () => {
    render(<Stepper etapes={[{ cle: 'a', libelle: 'A' }, { cle: 'b', libelle: 'B', termine: true }]} courante="a" onChange={() => {}} />);
    expect(screen.getByRole('button', { name: /A/ })).toHaveAttribute('aria-current', 'step');
  });
});
