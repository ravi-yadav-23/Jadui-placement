import React from 'react'

export default function TopSkillGapsCard({ skillGaps }) {
  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <h3 className="font-semibold text-white mb-3">Top Skill Gaps</h3>
      {!skillGaps?.length ? (
        <p className="text-sm text-muted">No major skill gaps detected yet. Upload resume for personalized insights.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {skillGaps.slice(0, 8).map((gap) => (
            <span key={gap} className="text-xs rounded-full border border-warning/30 bg-warning/10 px-3 py-1 text-warning">
              {gap}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
