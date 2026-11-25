import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import type { ReactNode } from 'react'

import { THEME_SCRIPT } from '@/features/auth/theme'
import Providers from './providers'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-sans', display: 'swap' })

export const metadata: Metadata = {
  title: { default: 'Jadui Placement', template: '%s · Jadui Placement' },
  description: 'Prepare for software engineering placements: a study plan built around your time, mock interviews '
    + 'scored with evidence, an honest resume review, and a coach that knows your progress.',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
