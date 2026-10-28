import { useEffect, useState } from 'react'
import { fetchUsers, type UserListItem } from '../api/admin'

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserListItem[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchUsers()
      .then(setUsers)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  return (
    <section className="card">
      <h2>Użytkownicy</h2>
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
      <ul className="status-list">
        {users.map((user) => (
          <li key={user.id} className="status-row">
            <span>{user.login}</span>
            <span className="status-label">
              {user.role}
              {user.is_blocked && ' · zablokowany'}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
