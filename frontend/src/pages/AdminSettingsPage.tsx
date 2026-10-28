import { useEffect, useState } from 'react'
import { fetchSecuritySettings, type SecuritySettings } from '../api/admin'

export default function AdminSettingsPage() {
  const [settings, setSettings] = useState<SecuritySettings | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchSecuritySettings()
      .then(setSettings)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  const rows: [string, string][] = settings
    ? [
        ['Minimalna długość hasła', `${settings.min_password_length} znaków`],
        ['Zakaz dat i lat 1950–2030', settings.date_rule_enabled ? 'włączony' : 'wyłączony'],
        [
          'Ważność hasła',
          settings.password_validity_days > 0
            ? `${settings.password_validity_days} dni`
            : 'wyłączona',
        ],
        ['Wylogowanie po bezczynności', `${settings.idle_timeout_minutes} min`],
      ]
    : []

  return (
    <section className="card">
      <h2>Ustawienia bezpieczeństwa</h2>
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
      <ul className="status-list">
        {rows.map(([label, value]) => (
          <li key={label} className="status-row">
            <span>{label}</span>
            <span className="status-label">{value}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
