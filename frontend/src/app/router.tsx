// Routes de l'application. Les pages sont gardées par rôle via <RequireAuth role=…>.
import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { Spinner } from '@/design-system/components';
import { Layout } from './Layout';
import { RequireAuth } from './RequireAuth';
import { LoginPage } from '@/features/auth/LoginPage';
import { DemandesListPage } from '@/features/demandes/DemandesListPage';
import { DemandeDetailPage } from '@/features/demandes/DemandeDetailPage';
import { NotificationsPage } from '@/features/notifications/NotificationsPage';

// La page Reporting embarque la bibliothèque de graphiques : chargée à la demande (chunk séparé).
// eslint-disable-next-line react-refresh/only-export-components -- import paresseux colocalisé avec le routeur
const ReportingPage = lazy(() =>
  import('@/features/reporting/ReportingPage').then((m) => ({ default: m.ReportingPage })),
);

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: (
      <RequireAuth>
        <Layout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/demandes" replace /> },
      { path: 'demandes', element: <DemandesListPage /> },
      { path: 'demandes/:id', element: <DemandeDetailPage /> },
      { path: 'notifications', element: <NotificationsPage /> },
      {
        path: 'reporting',
        element: (
          <Suspense fallback={<Spinner label="Chargement du reporting…" />}>
            <ReportingPage />
          </Suspense>
        ),
      },
      { path: '*', element: <Navigate to="/demandes" replace /> },
    ],
  },
]);
