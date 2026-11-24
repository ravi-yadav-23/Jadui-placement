'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, type ReactNode } from 'react'

/** React Query handles fetching, caching, polling and refetching for the v2 features. */
export default function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } }),
  )
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
