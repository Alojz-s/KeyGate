import { apiRequest } from './client'

export interface Article {
  id: number
  title: string
  content: string
}

export function fetchArticles(): Promise<Article[]> {
  return apiRequest<Article[]>('GET', '/articles')
}

export function createArticle(title: string, content: string): Promise<Article> {
  return apiRequest<Article>('POST', '/articles', { title, content })
}
