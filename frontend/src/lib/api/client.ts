/**
 * The one way the frontend calls the FastAPI backend.
 *
 * - Calls the backend directly (no Next.js proxy routes in between).
 * - Attaches the Supabase access token as `Authorization: Bearer ...`.
 * - Turns the backend's error shape `{ error: { code, message } }` into an ApiError.
 */
import { supabase } from '@/lib/supabase'

const BASE_URL = (process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message)
  }
}

async function accessToken(): Promise<string | null> {
  // The Playwright E2E run has no Supabase Auth; it builds the app with a token signed by the
  // test backend's secret. Never set this variable for a real deployment.
  const e2eToken = process.env.NEXT_PUBLIC_E2E_ACCESS_TOKEN
  if (e2eToken) return e2eToken
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
