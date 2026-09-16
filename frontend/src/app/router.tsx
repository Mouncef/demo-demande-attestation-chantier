// Routes de l'application. Les pages sont gardées par rôle via <RequireAuth role=…>.
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { Layout } from './Layout';
import { RequireAuth } from './RequireAuth';
import { LoginPage } from '@/features/auth/LoginPage';
import { DemandesListPage } from '@/features/demandes/DemandesListPage';
import { DemandeDetailPage } from '@/features/demandes/DemandeDetailPage';
import { NotificationsPage } from '@/features/notifications/NotificationsPage';

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
      { path: '*', element: <Navigate to="/demandes" replace /> },
    ],
  },
]);
