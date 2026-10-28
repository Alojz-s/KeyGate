import { createBrowserRouter } from 'react-router'
import PermissionRoute from './auth/PermissionRoute'
import ProtectedRoute from './auth/ProtectedRoute'
import Layout from './components/Layout'
import AdminSettingsPage from './pages/AdminSettingsPage'
import AdminUsersPage from './pages/AdminUsersPage'
import ArticlesPage from './pages/ArticlesPage'
import ChangePasswordPage from './pages/ChangePasswordPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import NewArticlePage from './pages/NewArticlePage'

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <Layout />,
        children: [
          { path: '/', element: <HomePage /> },
          { path: '/change-password', element: <ChangePasswordPage /> },
          {
            element: <PermissionRoute permission="articles.read" />,
            children: [{ path: '/articles', element: <ArticlesPage /> }],
          },
          {
            element: <PermissionRoute permission="articles.write" />,
            children: [{ path: '/articles/new', element: <NewArticlePage /> }],
          },
          {
            element: <PermissionRoute permission="users.manage" />,
            children: [{ path: '/admin/users', element: <AdminUsersPage /> }],
          },
          {
            element: <PermissionRoute permission="settings.manage" />,
            children: [{ path: '/admin/settings', element: <AdminSettingsPage /> }],
          },
        ],
      },
    ],
  },
])
