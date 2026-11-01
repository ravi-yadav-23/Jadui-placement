import { supabase } from './supabase';

/**
 * A wrapper around native fetch that automatically attaches the Supabase JWT
 * and optional admin session token.
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

  if (typeof window !== 'undefined') {
    const adminToken = sessionStorage.getItem('admin_token');
    if (adminToken) {
      headers.set('X-Admin-Token', adminToken);
    }
  }
  
  return fetch(url, {
    ...options,
    headers
  });
}
