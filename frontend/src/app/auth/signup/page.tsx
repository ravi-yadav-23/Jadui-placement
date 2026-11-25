'use client'

import Link from 'next/link'
import { Suspense } from 'react'

import { AuthLayout, SignupForm } from '@/features/auth/AuthForms'

export default function SignupPage() {
  return (
    <AuthLayout title="Create your account" subtitle="Free. Your data stays private to your account."
      footer={<>Already have an account? <Link href="/auth/login" className="font-medium text-primary hover:underline">Sign in</Link></>}>
      <Suspense><SignupForm /></Suspense>
    </AuthLayout>
  )
}
