'use client'

import { Suspense } from 'react'

import { PageHeader } from '@/components/ui'
import HistoryList from '@/features/interview/components/HistoryList'
import TrackPicker from '@/features/interview/components/TrackPicker'

/** Mock interviews: pick a track and start, or reopen a past interview. */
export default function InterviewHomePage() {
  return (
    <div className="space-y-8">
      <PageHeader title="Mock interviews" description="Practise the rounds of a campus interview. Answers are scored against the key points a strong answer covers, and feedback quotes your own words." />
      <Suspense><TrackPicker /></Suspense>
      <HistoryList />
    </div>
  )
}
