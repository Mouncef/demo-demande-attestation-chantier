// Point d'entrée : monte l'application React avec ses providers.
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './app/App';
import './design-system/base.css';
import './design-system/components.css';
import './app/layout.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
