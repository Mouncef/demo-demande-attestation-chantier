import type { ReactNode } from 'react';

const ICONES = { info: 'ℹ️', success: '✅', warning: '⚠️', danger: '⛔' } as const;

export function Alert({ type = 'info', children }: { type?: keyof typeof ICONES; children: ReactNode }) {
  return (
    <div className={`alert alert--${type}`} role={type === 'danger' ? 'alert' : 'status'}>
      <span aria-hidden>{ICONES[type]}</span>
      <div className="grow">{children}</div>
    </div>
  );
}
