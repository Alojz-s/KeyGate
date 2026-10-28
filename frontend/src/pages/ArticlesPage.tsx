import { useEffect, useState } from 'react'
import { fetchArticles, type Article } from '../api/articles'

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchArticles()
      .then(setArticles)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  return (
    <section className="card">
      <h2>Artykuły</h2>
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
      {articles.map((article) => (
        <article key={article.id} className="article">
          <h3>{article.title}</h3>
          <p>{article.content}</p>
        </article>
      ))}
    </section>
  )
}
