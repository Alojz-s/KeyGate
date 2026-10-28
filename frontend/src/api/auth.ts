import { apiRequest } from './client'

export interface Me {
  id: number
  login: string
  role: string
  permissions: string[]
  must_change_password: boolean
  idle_timeout_minutes: number
}

export function fetchMe(): Promise<Me> {
  return apiRequest<Me>('GET', '/auth/me')
}

export function login(login: string, password: string): Promise<Me> {
  return apiRequest<Me>('POST', '/auth/login', { login, password })
}

export function logout(): Promise<void> {
  return apiRequest<void>('POST', '/auth/logout')
}

export interface PasswordPolicy {
  min_password_length: number
  max_password_length: number
  date_rule_enabled: boolean
  requirements: string[]
}

// Bez ciasteczka: endpoint jest publiczny, a sesja z wymaganą zmianą hasła dostałaby 403.
export function fetchPasswordPolicy(): Promise<PasswordPolicy> {
  return apiRequest<PasswordPolicy>('GET', '/auth/password-policy', undefined, 'omit')
}

export function changePassword(
  oldPassword: string,
  newPassword: string,
  newPasswordConfirm: string,
): Promise<void> {
  return apiRequest<void>('POST', '/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
    new_password_confirm: newPasswordConfirm,
  })
}
