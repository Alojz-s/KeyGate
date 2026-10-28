import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { changePassword, fetchPasswordPolicy } from '../api/auth'
import { ApiError, type Violation } from '../api/client'
import { useAuth } from '../auth/AuthContext'

export default function ChangePasswordPage() {
  const { user, refreshUser } = useAuth()
  const navigate = useNavigate()
  const [requirements, setRequirements] = useState<string[]>([])
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [violations, setViolations] = useState<Violation[]>([])
  const [submitting, setSubmitting] = useState(false)
  const forced = user?.must_change_password ?? false

  useEffect(() => {
    fetchPasswordPolicy()
      .then((policy) => setRequirements(policy.requirements))
      .catch(() => setRequirements([]))
  }, [])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setViolations([])
    setSubmitting(true)
    try {
      await changePassword(oldPassword, newPassword, newPasswordConfirm)
      await refreshUser()
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setViolations(err instanceof ApiError ? err.violations : [])
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="card login-form" onSubmit={handleSubmit}>
      <h2>Zmiana hasła</h2>
      {forced && <p className="notice">Przed dalszą pracą musisz ustawić nowe hasło.</p>}
      {requirements.length > 0 && (
        <ul className="hint-list">
          {requirements.map((requirement) => (
            <li key={requirement}>{requirement}</li>
          ))}
        </ul>
      )}
      <label>
        Obecne hasło
        <input
          name="old_password"
          type="password"
          autoComplete="current-password"
          value={oldPassword}
          onChange={(e) => setOldPassword(e.target.value)}
          required
        />
      </label>
      <label>
        Nowe hasło
        <input
          name="new_password"
          type="password"
          autoComplete="new-password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          required
        />
      </label>
      {violations.length > 0 && (
        <ul className="hint-list error-message">
          {violations.map((violation) => (
            <li key={violation.code}>{violation.message}</li>
          ))}
        </ul>
      )}
      <label>
        Powtórz nowe hasło
        <input
          name="new_password_confirm"
          type="password"
          autoComplete="new-password"
          value={newPasswordConfirm}
          onChange={(e) => setNewPasswordConfirm(e.target.value)}
          required
        />
      </label>
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
      <button type="submit" disabled={submitting}>
        Zmień hasło
      </button>
    </form>
  )
}
