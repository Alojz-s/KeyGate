import { Outlet } from 'react-router'
import ForbiddenPage from '../pages/ForbiddenPage'
import { useAuth } from './AuthContext'
import { hasPermission, type Permission } from './permissions'

export default function PermissionRoute({ permission }: { permission: Permission }) {
  const { user } = useAuth()
  return hasPermission(user, permission) ? <Outlet /> : <ForbiddenPage />
}
