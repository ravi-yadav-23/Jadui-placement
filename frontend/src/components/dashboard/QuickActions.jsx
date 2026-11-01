import React from 'react'
import Link from 'next/link'
import { cn } from '@/lib/utils'

export default function QuickActions() {
  return (
    <div>
      <h3 className="font-semibold text-white mb-4">Quick Actions</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {[
          { label: 'Upload Resume',   href: '/dashboard/resume',    emoji: '📄', color: 'hover:border-primary/40 hover:bg-primary/5'    },
          { label: 'Start Interview', href: '/dashboard/interview', emoji: '🎤', color: 'hover:border-accent/40 hover:bg-accent/5'      },
          { label: 'Ask AI Mentor',   href: '/dashboard/chat',      emoji: '🧠', color: 'hover:border-secondary/40 hover:bg-secondary/5'},
          { label: 'GitHub profile',  href: '/dashboard/github-profile', emoji: '🐙', color: 'hover:border-primary/40 hover:bg-primary/5' },
          { label: 'View Progress',   href: '/dashboard/progress',  emoji: '📈', color: 'hover:border-success/40 hover:bg-success/5'    },
        ].map((action) => (
          <Link
            key={action.label}
            href={action.href}
            className={cn(
              'bg-card border border-border rounded-xl p-4 flex flex-col items-center gap-2',
              'transition-all duration-200 text-center group',
              action.color
            )}
          >
            <span className="text-2xl group-hover:scale-110 transition-transform duration-200">{action.emoji}</span>
            <span className="text-xs font-medium text-white">{action.label}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
