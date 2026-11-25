'use client'

/**
 * Who is signed in. Wraps Supabase Auth's session and keeps it up to date (sign in/out in another tab, token
 * refresh). In the E2E run there is no Supabase: a fixed test user stands in, matching the backend test token.
 */
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { User } from '@supabase/supabase-js'

import { E2E_TOKEN, supabase } from '@/lib/supabase'

type AuthUser = { id: string; email: string; name: string }
type AuthState = { user: AuthUser | null; loading: boolean; configured: boolean; signOut: () => Promise<void> }

const AuthContext = createContext<AuthState>({ user: null, loading: true, configured: false, signOut: async () => {} })

function toUser(user: User): AuthUser {
  const email = user.email ?? ''
  const name = (user.user_metadata?.full_name as string | undefined) || email.split('@')[0]
  return { id: user.id, email, name }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (E2E_TOKEN) {
      setUser({ id: 'e2e-user', email: 'e2e@test.dev', name: 'Test Student' })
      setLoading(false)
      return
    }
    if (!supabase) {
      setLoading(false)
      return
    }
    supabase.auth.getSession().then(({ data }) => {
      setUser(data.session ? toUser(data.session.user) : null)
      setLoading(false)
    })
    const { data } = supabase.auth.onAuthStateChange((_event, session) => setUser(session ? toUser(session.user) : null))
    return () => data.subscription.unsubscribe()
  }, [])

  const signOut = async () => {
    await supabase?.auth.signOut()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, configured: Boolean(supabase || E2E_TOKEN), signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
