// Routes de l'application. Les pages sont gardées par rôle via <RequireAuth role=…>.
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { Layout } from './Layout';
import { RequireAuth } from './RequireAuth';
import { LoginPage } from '@/features/auth/LoginPage';
import { AccueilPage } from '@/features/accueil/AccueilPage';

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
      { index: true, element: <AccueilPage /> },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
]);
