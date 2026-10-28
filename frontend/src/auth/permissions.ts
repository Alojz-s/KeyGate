import type { Me } from '../api/auth'

export type Permission = 'articles.read' | 'articles.write' | 'users.manage' | 'settings.manage'

// Tylko do ukrywania elementów UI - uprawnienia egzekwuje backend.
export function hasPermission(user: Me | null, permission: Permission): boolean {
  return user?.permissions.includes(permission) ?? false
}
