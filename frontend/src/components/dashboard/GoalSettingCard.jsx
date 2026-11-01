import React from 'react'

export default function GoalSettingCard({ goalRole, setGoalRole, goalDate, setGoalDate, saveGoal, goalSaved }) {
  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <h3 className="font-semibold text-white mb-3">Goal Setting</h3>
      <div className="space-y-3">
        <input
          value={goalRole}
          onChange={(e) => setGoalRole(e.target.value)}
          placeholder="Target role (e.g., SDE-1)"
          className="w-full rounded-lg border border-border bg-surface/40 px-3 py-2 text-sm text-white outline-none focus:border-primary"
        />
        <input
          type="date"
          value={goalDate}
          onChange={(e) => setGoalDate(e.target.value)}
          className="w-full rounded-lg border border-border bg-surface/40 px-3 py-2 text-sm text-white outline-none focus:border-primary"
        />
        <button onClick={() => saveGoal(goalRole, goalDate)} className="btn-primary w-full text-sm py-2">
          {goalSaved ? 'Saved' : 'Save Goal'}
        </button>
      </div>
    </div>
  )
}
