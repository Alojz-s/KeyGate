import { useEffect, useState } from 'react'
import { fetchHealth, type HealthResponse } from '../api/health'

type State =
  | { kind: 'loading' }
  | { kind: 'loaded'; health: HealthResponse }
  | { kind: 'unreachable'; message: string }

function StatusBadge({ label, ok }: { label: string; ok: boolean | null }) {
  const modifier = ok === null ? 'pending' : ok ? 'ok' : 'error'
  const text = ok === null ? 'sprawdzanie…' : ok ? 'ok' : 'błąd'
  return (
    <li className="status-row">
      <span className="status-label">{label}</span>
      <span className={`status-badge status-badge--${modifier}`}>{text}</span>
    </li>
  )
}

export default function HomePage() {
  const [state, setState] = useState<State>({ kind: 'loading' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    fetchHealth(controller.signal)
      .then((health) => setState({ kind: 'loaded', health }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setState({
          kind: 'unreachable',
          message: error instanceof Error ? error.message : String(error),
        })
      })
    return () => controller.abort()
  }, [attempt])

  const refresh = () => {
    setState({ kind: 'loading' })
    setAttempt((n) => n + 1)
  }

  let backendOk: boolean | null = null
  let databaseOk: boolean | null = null
  if (state.kind === 'loaded') {
    backendOk = state.health.status === 'ok'
    databaseOk = state.health.database === 'ok'
  } else if (state.kind === 'unreachable') {
    backendOk = false
    databaseOk = false
  }

  return (
    <main className="home">
      <h1>KeyGate</h1>
      <p className="subtitle">Firmowy portal z artykułami</p>

      <section className="card" aria-labelledby="status-heading">
        <h2 id="status-heading">Status systemu</h2>
        <ul className="status-list">
          <StatusBadge label="Backend" ok={backendOk} />
          <StatusBadge label="Baza danych" ok={databaseOk} />
        </ul>
        {state.kind === 'unreachable' && (
          <p className="error-message">Brak połączenia z backendem ({state.message}).</p>
        )}
        <button type="button" onClick={refresh} disabled={state.kind === 'loading'}>
          Odśwież
        </button>
      </section>
    </main>
  )
}
