import { apiRequest } from './client'

export interface UserListItem {
  id: number
  login: string
  role: string
  is_blocked: boolean
}

export interface SecuritySettings {
  min_password_length: number
  date_rule_enabled: boolean
  password_validity_days: number
  idle_timeout_minutes: number
}

export function fetchUsers(): Promise<UserListItem[]> {
  return apiRequest<UserListItem[]>('GET', '/admin/users')
}

export function fetchSecuritySettings(): Promise<SecuritySettings> {
  return apiRequest<SecuritySettings>('GET', '/admin/settings/security')
}
