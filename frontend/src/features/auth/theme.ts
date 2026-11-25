'use client'

import { useEffect, useState } from 'react'

export type Theme = 'light' | 'dark' | 'system'
const KEY = 'jadui-theme'

/** Runs before React (inline in <head>) so the page never flashes the wrong theme. */
export const THEME_SCRIPT = `(function(){try{var t=localStorage.getItem('${KEY}')||'system';var d=t==='dark'||(t==='system'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.classList.toggle('dark',d)}catch(e){}})()`

function apply(theme: Theme) {
  const dark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  document.documentElement.classList.toggle('dark', dark)
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>('system')
  useEffect(() => { setThemeState((localStorage.getItem(KEY) as Theme) || 'system') }, [])
  useEffect(() => {
    if (theme !== 'system') return
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = () => apply('system')
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [theme])
  const setTheme = (next: Theme) => {
    localStorage.setItem(KEY, next)
    setThemeState(next)
    apply(next)
  }
  return { theme, setTheme }
}
