import { supabase } from './supabase';

/**
 * A wrapper around native fetch that automatically attaches the Supabase JWT.
 * Works for both Next.js API proxy routes and direct backend calls.
 */
export async function fetchWithAuth(url, options = {}) {
  let token = null;
  if (supabase) {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      token = session?.access_token;
    } catch {
      token = null;
    }
  }
  
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  
  return fetch(url, {
    ...options,
    headers
  });
}
