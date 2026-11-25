'use client'

import { AuthLayout, ResetForm } from '@/features/auth/AuthForms'

export default function ResetPage() {
  return (
    <AuthLayout title="Set a new password">
      <ResetForm />
    </AuthLayout>
  )
}
