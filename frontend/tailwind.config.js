/**
 * Design tokens live in src/app/globals.css as CSS variables (light + dark).
 * Tailwind only maps names to those variables, so every component switches theme automatically.
 * Names: bg (page), surface (cards), subtle (quiet fills), border, fg (text), primary (jade accent), status colours.
 * `muted`, `card`, `background` and `error` are aliases kept for the resume/interview components.
 */
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`

/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class'],
  content: ['./src/**/*.{js,jsx,ts,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        bg: v('bg'),
        background: v('bg'),
        surface: v('surface'),
        card: v('surface'),
        subtle: v('subtle'),
        border: { DEFAULT: v('border'), strong: v('border-strong') },
        fg: { DEFAULT: v('fg'), muted: v('fg-muted'), subtle: v('fg-subtle') },
        muted: v('fg-muted'),
        primary: { DEFAULT: v('primary'), hover: v('primary-hover'), fg: v('primary-fg'), soft: v('primary-soft'),
                   'soft-fg': v('primary-soft-fg') },
        success: { DEFAULT: v('success'), soft: v('success-soft') },
        warning: { DEFAULT: v('warning'), soft: v('warning-soft') },
        danger: { DEFAULT: v('danger'), soft: v('danger-soft') },
        error: { DEFAULT: v('danger'), soft: v('danger-soft') },
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      fontSize: {
        xs: ['12px', '16px'],
        sm: ['13px', '20px'],
        base: ['14px', '22px'],
        md: ['15px', '24px'],
        lg: ['17px', '26px'],
        xl: ['20px', '28px'],
        '2xl': ['24px', '32px'],
        '3xl': ['30px', '38px'],
        '4xl': ['40px', '48px'],
        '5xl': ['52px', '58px'],
        '6xl': ['64px', '68px'],
      },
      borderRadius: { DEFAULT: '6px', md: '8px', lg: '10px', xl: '12px' },
      keyframes: {
        'fade-up': { from: { opacity: '0', transform: 'translateY(8px)' }, to: { opacity: '1', transform: 'none' } },
        scan: { '0%': { top: '0%' }, '100%': { top: '100%' } },
        fill: { from: { transform: 'scaleX(0)' }, to: { transform: 'scaleX(1)' } },
        dot: { '0%, 80%, 100%': { opacity: '0.25' }, '40%': { opacity: '1' } },
      },
      animation: {
        'fade-up': 'fade-up 0.6s ease-out both',
        scan: 'scan 1.6s ease-in-out infinite alternate',
        dot: 'dot 1.2s ease-in-out infinite',
        fill: 'fill 1s linear both', // duration set inline
      },
      boxShadow: {
        xs: '0 1px 2px rgb(0 0 0 / 0.04)',
        sm: '0 1px 3px rgb(0 0 0 / 0.06), 0 1px 2px rgb(0 0 0 / 0.04)',
        pop: '0 8px 24px rgb(0 0 0 / 0.12), 0 2px 6px rgb(0 0 0 / 0.06)',
      },
    },
  },
  plugins: [],
}
