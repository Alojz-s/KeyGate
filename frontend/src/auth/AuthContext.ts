import { createContext, useContext } from 'react'
import type { Me } from '../api/auth'

export interface AuthContextValue {
  user: Me | null
  loading: boolean
  /** Komunikat dla strony logowania, np. o wylogowaniu z powodu bezczynności. */
  notice: string | null
  login: (login: string, password: string) => Promise<void>
  logout: (notice?: string) => Promise<void>
  refreshUser: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth wymaga AuthProvider')
  return value
}
