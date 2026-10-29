import { useState, type FormEvent } from 'react'
import { Navigate } from 'react-router'
import { useAuth } from '../auth/AuthContext'
import Brand from '../components/Brand'

export default function LoginPage() {
  const { user, loading, notice, login } = useAuth()
  const [loginName, setLoginName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (loading) return null
  if (user) return <Navigate to="/" replace />

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(loginName, password)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setPassword('')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="home">
      <Brand />

      <form className="card login-form" onSubmit={handleSubmit}>
        <h2>Logowanie</h2>
        {notice && <p className="notice">{notice}</p>}
        <label>
          Login
          <input
            name="login"
            autoComplete="username"
            value={loginName}
            onChange={(e) => setLoginName(e.target.value)}
            required
          />
        </label>
        <label>
          Hasło
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        {error && (
          <p className="error-message" role="alert">
            {error}
          </p>
        )}
        <button type="submit" disabled={submitting}>
          Zaloguj
        </button>
      </form>
    </main>
  )
}
