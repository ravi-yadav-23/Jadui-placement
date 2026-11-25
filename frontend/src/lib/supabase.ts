import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const url = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

/** Supabase Auth client (the backend verifies its access tokens). Null when not configured. */
export const supabase: SupabaseClient | null = url && anonKey ? createClient(url, anonKey) : null

/** The Playwright E2E run has no Supabase; it builds the app with a test token instead. Never set in production. */
export const E2E_TOKEN = process.env.NEXT_PUBLIC_E2E_ACCESS_TOKEN || ''
