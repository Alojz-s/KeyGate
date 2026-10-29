import { useEffect, useState, type FormEvent } from 'react'
import { fetchArticles, updateArticle, type Article } from '../api/articles'
import { useAuth } from '../auth/AuthContext'
import { hasPermission } from '../auth/permissions'

export default function ArticlesPage() {
  const { user } = useAuth()
  const canWrite = hasPermission(user, 'articles.write')
  const [articles, setArticles] = useState<Article[]>([])
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<Article | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchArticles()
      .then(setArticles)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  const handleSave = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!editing) return
    setError(null)
    setSaving(true)
    try {
      const saved = await updateArticle(editing.id, editing.title, editing.content)
      setArticles((prev) => prev.map((a) => (a.id === saved.id ? saved : a)))
      setEditing(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="card">
      <h2>Artykuły</h2>
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
      <div className="article-list">
        {articles.map((article) =>
          editing?.id === article.id ? (
            <form key={article.id} className="article login-form" onSubmit={handleSave}>
              <label>
                Tytuł
                <input
                  name="title"
                  maxLength={200}
                  value={editing.title}
                  onChange={(e) => setEditing({ ...editing, title: e.target.value })}
                  required
                />
              </label>
              <label>
                Treść
                <textarea
                  name="content"
                  rows={6}
                  value={editing.content}
                  onChange={(e) => setEditing({ ...editing, content: e.target.value })}
                  required
                />
              </label>
              <div className="form-actions">
                <button type="submit" disabled={saving}>
                  Zapisz
                </button>
                <button
                  type="button"
                  className="button-secondary"
                  disabled={saving}
                  onClick={() => setEditing(null)}
                >
                  Anuluj
                </button>
              </div>
            </form>
          ) : (
            <article key={article.id} className="article">
              <h3>{article.title}</h3>
              <p>{article.content}</p>
              {canWrite && (
                <button
                  type="button"
                  className="button-small button-secondary"
                  onClick={() => setEditing(article)}
                >
                  Edytuj
                </button>
              )}
            </article>
          ),
        )}
      </div>
    </section>
  )
}
