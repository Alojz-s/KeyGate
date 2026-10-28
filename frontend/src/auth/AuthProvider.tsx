import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { fetchMe, login as apiLogin, logout as apiLogout, type Me } from '../api/auth'
import { setUnauthorizedHandler } from '../api/client'
import { AuthContext } from './AuthContext'

const IDLE_NOTICE = 'Wylogowano z powodu bezczynności'
const ACTIVITY_EVENTS = ['mousemove', 'keydown', 'click'] as const

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    setUnauthorizedHandler((code) => {
      setUser(null)
      if (code === 'session_expired') setNotice(IDLE_NOTICE)
    })
    fetchMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (loginName: string, password: string) => {
    setNotice(null)
    setUser(await apiLogin(loginName, password))
  }, [])

  const logout = useCallback(async (reason?: string) => {
    setUser(null)
    setNotice(reason ?? null)
    await apiLogout().catch(() => undefined)
  }, [])

  // Tylko licznik po stronie klienta - bez odpytywania API w tle.
  useEffect(() => {
    if (!user) return
    const timeoutMs = user.idle_timeout_minutes * 60_000
    let timer: number | undefined
    const reset = () => {
      window.clearTimeout(timer)
      timer = window.setTimeout(() => logout(IDLE_NOTICE), timeoutMs)
    }
    reset()
    for (const event of ACTIVITY_EVENTS) window.addEventListener(event, reset)
    return () => {
      window.clearTimeout(timer)
      for (const event of ACTIVITY_EVENTS) window.removeEventListener(event, reset)
    }
  }, [user, logout])

  const value = useMemo(
    () => ({ user, loading, notice, login, logout }),
    [user, loading, notice, login, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
