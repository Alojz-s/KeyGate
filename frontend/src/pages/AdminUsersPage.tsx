import { useEffect, useState, type FormEvent } from 'react'
import {
  ADMIN_LOGIN,
  blockUser,
  createUser,
  deleteUser,
  fetchRoles,
  fetchUsers,
  resetPassword,
  unblockUser,
  updateUser,
  type Role,
  type UserListItem,
} from '../api/admin'

interface IssuedPassword {
  login: string
  password: string
}

const byLogin = (a: UserListItem, b: UserListItem) => a.login.localeCompare(b.login)

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserListItem[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [error, setError] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [issued, setIssued] = useState<IssuedPassword | null>(null)
  const [newLogin, setNewLogin] = useState('')
  const [newRoleId, setNewRoleId] = useState('')

  useEffect(() => {
    Promise.all([fetchUsers(), fetchRoles()])
      .then(([loadedUsers, loadedRoles]) => {
        setUsers(loadedUsers)
        setRoles(loadedRoles)
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  const run = async (action: () => Promise<void>, showError = setError) => {
    setError(null)
    setFormError(null)
    setBusy(true)
    try {
      await action()
    } catch (err) {
      showError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const replaceUser = (updated: UserListItem) =>
    setUsers((current) => current.map((u) => (u.id === updated.id ? updated : u)))

  const handleCreate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void run(async () => {
      const { one_time_password, ...created } = await createUser(newLogin, Number(newRoleId))
      setUsers((current) => [...current, created].sort(byLogin))
      setIssued({ login: created.login, password: one_time_password })
      setNewLogin('')
      setNewRoleId('')
    }, setFormError)
  }

  const handleRoleChange = (user: UserListItem, roleId: number) => {
    void run(async () => replaceUser(await updateUser(user.id, roleId)))
  }

  const handleToggleBlock = (user: UserListItem) => {
    void run(async () => replaceUser(await (user.is_blocked ? unblockUser : blockUser)(user.id)))
  }

  const handleReset = (user: UserListItem) => {
    const question = `Zresetować hasło użytkownika ${user.login}? Dotychczasowe hasło przestanie działać.`
    if (!window.confirm(question)) return
    void run(async () => {
      setIssued({ login: user.login, password: await resetPassword(user.id) })
    })
  }

  const handleDelete = (user: UserListItem) => {
    if (!window.confirm(`Usunąć użytkownika ${user.login}? Tej operacji nie można cofnąć.`)) return
    void run(async () => {
      await deleteUser(user.id)
      setUsers((current) => current.filter((u) => u.id !== user.id))
      setIssued((current) => (current?.login === user.login ? null : current))
    })
  }

  return (
    <>
      <section className="card">
        <h2>Użytkownicy</h2>
        {error && (
          <p className="error-message" role="alert">
            {error}
          </p>
        )}
        {issued && (
          <div className="otp-box" role="status">
            <p>
              Hasło jednorazowe dla <strong>{issued.login}</strong>:
            </p>
            <code className="otp-value">{issued.password}</code>
            <p>
              Skopiuj je teraz – nie zostanie pokazane ponownie. Jest ważne 24 godziny i działa
              jeden raz; po zalogowaniu użytkownik musi ustawić własne hasło.
            </p>
            <button type="button" className="button-small" onClick={() => setIssued(null)}>
              Zamknij
            </button>
          </div>
        )}
        <div className="table-scroll">
          <table className="users-table">
            <thead>
              <tr>
                <th>Login</th>
                <th>Rola</th>
                <th>Status</th>
                <th>Akcje</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => {
                const isProtected = user.login === ADMIN_LOGIN
                return (
                  <tr key={user.id}>
                    <td>{user.login}</td>
                    <td>
                      {isProtected ? (
                        user.role
                      ) : (
                        <select
                          aria-label={`Rola użytkownika ${user.login}`}
                          value={user.role_id}
                          disabled={busy}
                          onChange={(e) => handleRoleChange(user, Number(e.target.value))}
                        >
                          {roles.map((role) => (
                            <option key={role.id} value={role.id}>
                              {role.name}
                            </option>
                          ))}
                        </select>
                      )}
                    </td>
                    <td>
                      <span
                        className={`status-badge status-badge--${user.is_blocked ? 'error' : 'ok'}`}
                      >
                        {user.is_blocked ? 'zablokowany' : 'aktywny'}
                      </span>
                    </td>
                    <td>
                      {!isProtected && (
                        <div className="row-actions">
                          <button
                            type="button"
                            className="button-small button-secondary"
                            disabled={busy}
                            onClick={() => handleToggleBlock(user)}
                          >
                            {user.is_blocked ? 'Odblokuj' : 'Zablokuj'}
                          </button>
                          <button
                            type="button"
                            className="button-small button-secondary"
                            disabled={busy}
                            onClick={() => handleReset(user)}
                          >
                            Reset hasła
                          </button>
                          <button
                            type="button"
                            className="button-small button-danger"
                            disabled={busy}
                            onClick={() => handleDelete(user)}
                          >
                            Usuń
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </section>
      <form className="card login-form" onSubmit={handleCreate}>
        <h2>Nowy użytkownik</h2>
        <label>
          Login
          <input
            name="login"
            maxLength={64}
            autoComplete="off"
            value={newLogin}
            onChange={(e) => setNewLogin(e.target.value)}
            required
          />
        </label>
        <label>
          Rola
          <select
            name="role_id"
            value={newRoleId}
            onChange={(e) => setNewRoleId(e.target.value)}
            required
          >
            <option value="" disabled>
              Wybierz rolę
            </option>
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.name}
              </option>
            ))}
          </select>
        </label>
        {formError && (
          <p className="error-message" role="alert">
            {formError}
          </p>
        )}
        <button type="submit" disabled={busy}>
          Utwórz konto
        </button>
      </form>
    </>
  )
}
