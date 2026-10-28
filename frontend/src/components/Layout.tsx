import { NavLink, Outlet } from 'react-router'
import { useAuth } from '../auth/AuthContext'
import { hasPermission } from '../auth/permissions'

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <main className="home">
      <header className="user-bar">
        <span>
          Zalogowano jako <strong>{user?.login}</strong> ({user?.role})
        </span>
        <button type="button" onClick={() => logout()}>
          Wyloguj
        </button>
      </header>
      {!user?.must_change_password && (
        <nav className="main-nav">
          <NavLink to="/" end>
            Start
          </NavLink>
          {hasPermission(user, 'articles.read') && (
            <NavLink to="/articles" end>
              Artykuły
            </NavLink>
          )}
          {hasPermission(user, 'articles.write') && (
            <NavLink to="/articles/new">Nowy artykuł</NavLink>
          )}
          {hasPermission(user, 'users.manage') && <NavLink to="/admin/users">Użytkownicy</NavLink>}
          {hasPermission(user, 'settings.manage') && (
            <NavLink to="/admin/settings">Ustawienia</NavLink>
          )}
          <NavLink to="/change-password">Zmiana hasła</NavLink>
        </nav>
      )}
      <h1>KeyGate</h1>
      <p className="subtitle">Firmowy portal z artykułami</p>
      <Outlet />
    </main>
  )
}
