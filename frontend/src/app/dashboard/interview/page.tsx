'use client'

import { Mic } from 'lucide-react'

import HistoryList from '@/features/interview/components/HistoryList'
import TrackPicker from '@/features/interview/components/TrackPicker'

/** Mock interviews: pick a track and start, or reopen a past interview. */
export default function InterviewHomePage() {
  return (
    <div className="mx-auto max-w-4xl space-y-8">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-white">
          <Mic className="h-6 w-6 text-primary" /> Mock Interviews
        </h1>
        <p className="mt-1 text-sm text-muted">
          Practise the rounds of a campus interview. Every answer is scored against the key points a strong answer
          covers, and the feedback quotes your own words.
        </p>
      </header>
      <TrackPicker />
      <HistoryList />
    </div>
  )
}
