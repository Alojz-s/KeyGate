import { apiRequest } from './client'

export const ADMIN_LOGIN = 'ADMIN'

export interface UserListItem {
  id: number
  login: string
  role_id: number
  role: string
  is_blocked: boolean
}

export interface CreatedUser extends UserListItem {
  one_time_password: string
}

export interface Role {
  id: number
  name: string
}

export interface SecuritySettings {
  min_password_length: number
  date_rule_enabled: boolean
  password_validity_days: number
  idle_timeout_minutes: number
}

export function fetchRoles(): Promise<Role[]> {
  return apiRequest<Role[]>('GET', '/admin/roles')
}

export function fetchUsers(): Promise<UserListItem[]> {
  return apiRequest<UserListItem[]>('GET', '/admin/users')
}

export function createUser(login: string, roleId: number): Promise<CreatedUser> {
  return apiRequest<CreatedUser>('POST', '/admin/users', { login, role_id: roleId })
}

export function updateUser(id: number, roleId: number): Promise<UserListItem> {
  return apiRequest<UserListItem>('PATCH', `/admin/users/${id}`, { role_id: roleId })
}

export function blockUser(id: number): Promise<UserListItem> {
  return apiRequest<UserListItem>('POST', `/admin/users/${id}/block`)
}

export function unblockUser(id: number): Promise<UserListItem> {
  return apiRequest<UserListItem>('POST', `/admin/users/${id}/unblock`)
}

export function deleteUser(id: number): Promise<void> {
  return apiRequest<void>('DELETE', `/admin/users/${id}`)
}

export async function resetPassword(id: number): Promise<string> {
  const response = await apiRequest<{ one_time_password: string }>(
    'POST',
    `/admin/users/${id}/reset-password`,
  )
  return response.one_time_password
}

export function fetchSecuritySettings(): Promise<SecuritySettings> {
  return apiRequest<SecuritySettings>('GET', '/admin/settings/security')
}
