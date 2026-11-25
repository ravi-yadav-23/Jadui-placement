'use client'

import Link from 'next/link'

import { AuthLayout, ForgotForm } from '@/features/auth/AuthForms'

export default function ForgotPage() {
  return (
    <AuthLayout title="Reset your password" subtitle="We'll email you a link to set a new one."
      footer={<Link href="/auth/login" className="font-medium text-primary hover:underline">Back to sign in</Link>}>
      <ForgotForm />
    </AuthLayout>
  )
}
