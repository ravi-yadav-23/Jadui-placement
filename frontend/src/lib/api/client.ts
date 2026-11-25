/**
 * The one way the frontend calls the FastAPI backend.
 *
 * - Calls the backend directly (no Next.js proxy routes in between).
 * - Attaches the Supabase access token as `Authorization: Bearer ...`.
 * - Turns the backend's error shape `{ error: { code, message } }` into an ApiError.
 */
import { E2E_TOKEN, supabase } from '@/lib/supabase'

const BASE_URL = (process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message)
  }
}

async function accessToken(): Promise<string | null> {
  if (E2E_TOKEN) return E2E_TOKEN   // Playwright run only (see lib/supabase.ts)
  if (!supabase) return null
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = await accessToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')

  let response: Response
  try {
    response = await fetch(`${BASE_URL}/api/v2${path}`, { ...init, headers })
  } catch {
    throw new ApiError(0, 'network_error', 'Cannot reach the server. Is the backend running?')
  }

  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const error = body?.error
    // FastAPI's own validation errors use {detail: [...]} instead of our {error: ...} shape.
    const message = error?.message || (Array.isArray(body?.detail) ? body.detail[0]?.msg : null) || 'Request failed'
    throw new ApiError(response.status, error?.code || 'request_failed', message)
  }
  return body as T
}
