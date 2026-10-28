import { Link } from 'react-router'

export default function ForbiddenPage() {
  return (
    <section className="card">
      <h2>Brak dostępu (403)</h2>
      <p>Nie masz uprawnień do wyświetlenia tej strony.</p>
      <Link to="/">Wróć na stronę główną</Link>
    </section>
  )
}
