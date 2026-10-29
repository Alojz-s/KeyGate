import { useEffect, useState, type FormEvent } from 'react'
import { fetchSecuritySettings, updateSecuritySettings, type SecuritySettings } from '../api/admin'
import { ApiError, type Violation } from '../api/client'
import { useAuth } from '../auth/AuthContext'

type NumberField = 'min_password_length' | 'password_validity_days' | 'idle_timeout_minutes'

interface FormState {
  min_password_length: string
  date_rule_enabled: boolean
  password_validity_days: string
  idle_timeout_minutes: string
}

const NUMBER_FIELDS: { name: NumberField; label: string; min: number; max?: number }[] = [
  { name: 'min_password_length', label: 'Minimalna długość hasła', min: 15, max: 64 },
  { name: 'password_validity_days', label: 'Ważność hasła (dni, 0 = wył.)', min: 0 },
  { name: 'idle_timeout_minutes', label: 'Bezczynność sesji (min)', min: 1, max: 120 },
]

function toForm(settings: SecuritySettings): FormState {
  return {
    min_password_length: String(settings.min_password_length),
    date_rule_enabled: settings.date_rule_enabled,
    password_validity_days: String(settings.password_validity_days),
    idle_timeout_minutes: String(settings.idle_timeout_minutes),
  }
}

export default function AdminSettingsPage() {
  const { refreshUser } = useAuth()
  const [form, setForm] = useState<FormState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [violations, setViolations] = useState<Violation[]>([])
  const [saved, setSaved] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetchSecuritySettings()
      .then((settings) => setForm(toForm(settings)))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!form) return
    setError(null)
    setViolations([])
    setSaved(false)
    setSubmitting(true)
    try {
      const settings = await updateSecuritySettings({
        min_password_length: Number(form.min_password_length),
        date_rule_enabled: form.date_rule_enabled,
        password_validity_days: Number(form.password_validity_days),
        idle_timeout_minutes: Number(form.idle_timeout_minutes),
      })
      setForm(toForm(settings))
      setSaved(true)
      // Licznik bezczynności bierze limit z /auth/me – odświeżamy go dla bieżącej sesji.
      await refreshUser()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setViolations(err instanceof ApiError ? err.violations : [])
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="card login-form" onSubmit={handleSubmit}>
      <h2>Ustawienia bezpieczeństwa</h2>
      {form && (
        <>
          {NUMBER_FIELDS.map((field) => (
            <label key={field.name}>
              {field.label}
              <input
                name={field.name}
                type="number"
                min={field.min}
                max={field.max}
                value={form[field.name]}
                onChange={(e) => setForm({ ...form, [field.name]: e.target.value })}
                required
              />
            </label>
          ))}
          <label className="checkbox-label">
            <input
              name="date_rule_enabled"
              type="checkbox"
              checked={form.date_rule_enabled}
              onChange={(e) => setForm({ ...form, date_rule_enabled: e.target.checked })}
            />
            Zakaz dat i lat 1950–2030
          </label>
        </>
      )}
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
      {violations.length > 0 && (
        <ul className="hint-list error-message">
          {violations.map((violation, index) => (
            <li key={`${violation.code}-${index}`}>{violation.message}</li>
          ))}
        </ul>
      )}
      {saved && (
        <p className="notice" role="status">
          Zapisano ustawienia. Obowiązują od razu, także w otwartych sesjach.
        </p>
      )}
      <button type="submit" disabled={!form || submitting}>
        Zapisz
      </button>
    </form>
  )
}
