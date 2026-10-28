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
