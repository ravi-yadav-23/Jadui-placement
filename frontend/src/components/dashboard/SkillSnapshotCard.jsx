import React from 'react'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { ProgressBar } from '@/components/ui'

export default function SkillSnapshotCard({ skillData }) {
  return (
    <div className="bg-card border border-border rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-6 py-4 border-b border-border">
        <h3 className="font-semibold text-white">Skill Snapshot</h3>
        <Link href="/dashboard/progress" className="text-xs text-primary hover:underline flex items-center gap-1">
          Details <ArrowRight className="w-3 h-3" />
        </Link>
      </div>
      <div className="px-6 py-4 space-y-4">
        {skillData?.length === 0 ? (
          <p className="text-xs text-muted">Upload resumes to generate your personalized skill snapshot.</p>
        ) : skillData?.map((skill) => (
          <div key={skill.name}>
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-muted font-medium">{skill.name}</span>
              <span className="text-white font-semibold">{skill.level}%</span>
            </div>
            <ProgressBar value={skill.level} max={100} color={skill.level >= 75 ? 'success' : skill.level >= 50 ? 'primary' : 'warning'} />
          </div>
        ))}
      </div>
    </div>
  )
}
