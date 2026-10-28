import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from './AuthContext'

export default function ProtectedRoute() {
  const { user, loading } = useAuth()
  const { pathname } = useLocation()
  if (loading) return null
  if (!user) return <Navigate to="/login" replace />
  if (user.must_change_password && pathname !== '/change-password') {
    return <Navigate to="/change-password" replace />
  }
  return <Outlet />
}
