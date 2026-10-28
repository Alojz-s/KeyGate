import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { createArticle } from '../api/articles'

export default function NewArticlePage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await createArticle(title, content)
      navigate('/articles')
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="card login-form" onSubmit={handleSubmit}>
      <h2>Nowy artykuł</h2>
      <label>
        Tytuł
        <input
          name="title"
          maxLength={200}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
      </label>
      <label>
        Treść
        <textarea
          name="content"
          rows={6}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          required
        />
      </label>
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
      <button type="submit" disabled={submitting}>
        Opublikuj
      </button>
    </form>
  )
}
