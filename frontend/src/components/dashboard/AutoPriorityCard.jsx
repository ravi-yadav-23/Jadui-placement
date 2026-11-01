import React from 'react'

export default function AutoPriorityCard({ weakestTwoSkills, generateTodayPlan, generatingPlan }) {
  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <h3 className="font-semibold text-white mb-3">Auto Priority (Weakest 2)</h3>
      {weakestTwoSkills.length === 0 ? (
        <p className="text-sm text-muted">No weak skills detected yet.</p>
      ) : (
        <div className="space-y-2">
          {weakestTwoSkills.map((skill) => (
            <div key={skill} className="rounded-md border border-warning/20 bg-warning/5 px-3 py-2 text-sm text-warning">
              {skill}
            </div>
          ))}
        </div>
      )}
      <button onClick={() => generateTodayPlan(weakestTwoSkills)} className="btn-outline w-full mt-4 text-sm py-2">
        {generatingPlan ? 'Generating...' : 'Generate Today Plan'}
      </button>
    </div>
  )
}
