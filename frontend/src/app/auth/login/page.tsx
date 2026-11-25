'use client'

import Link from 'next/link'
import { Suspense } from 'react'

import { AuthLayout, LoginForm } from '@/features/auth/AuthForms'

export default function LoginPage() {
  return (
    <AuthLayout title="Sign in" subtitle="Welcome back. Pick up where you left off."
      footer={<>New here? <Link href="/auth/signup" className="font-medium text-primary hover:underline">Create an account</Link></>}>
      <Suspense><LoginForm /></Suspense>
    </AuthLayout>
  )
}
