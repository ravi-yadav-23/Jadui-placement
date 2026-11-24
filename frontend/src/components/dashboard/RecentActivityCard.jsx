import React from 'react'

export default function RecentActivityCard({ resumeHistory, interviewHistory }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-card border border-border rounded-xl p-5">
        <h3 className="font-semibold text-white mb-4">Recent Resume Uploads</h3>
        {resumeHistory?.length === 0 ? (
          <p className="text-sm text-muted">No resume uploads yet.</p>
        ) : (
          <div className="space-y-3">
            {resumeHistory?.slice(0, 4).map((item) => (
              <div key={item.result_id} className="rounded-lg border border-border bg-surface/40 p-3">
                <p className="text-sm text-white font-medium">{item.candidate_name}</p>
                <p className="text-xs text-muted mt-1">{item.role_target || 'General Role'} • Score {item.score}/100</p>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="bg-card border border-border rounded-xl p-5">
        <h3 className="font-semibold text-white mb-4">Recent Interviews</h3>
        {interviewHistory?.length === 0 ? (
          <p className="text-sm text-muted">No interview sessions yet.</p>
        ) : (
          <div className="space-y-3">
            {interviewHistory?.slice(0, 4).map((item) => (
              <div key={item.session_id} className="rounded-lg border border-border bg-surface/40 p-3">
                <p className="text-sm text-white font-medium">{item.role}</p>
                <p className="text-xs text-muted mt-1">Score {item.overall_score}/100</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
