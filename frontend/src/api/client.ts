export class ApiError extends Error {
  readonly status: number
  readonly code?: string

  constructor(status: number, message: string, code?: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

type UnauthorizedHandler = (code?: string) => void

let onUnauthorized: UnauthorizedHandler = () => {}

export function setUnauthorizedHandler(handler: UnauthorizedHandler): void {
  onUnauthorized = handler
}

export async function apiRequest<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    credentials: 'include',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (response.ok) {
    return (response.status === 204 ? undefined : await response.json()) as T
  }

  const error = (await response.json().catch(() => null)) as { detail?: unknown; code?: string } | null
  if (response.status === 401) onUnauthorized(error?.code)
  const message =
    typeof error?.detail === 'string' ? error.detail : `Błąd serwera (HTTP ${response.status})`
  throw new ApiError(response.status, message, error?.code)
}
