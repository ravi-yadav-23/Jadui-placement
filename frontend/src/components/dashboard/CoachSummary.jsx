import { Sparkles } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function CoachSummary({ readinessBand, nextBestAction }) {
  return (
    <div className="lg:col-span-2 glass border border-border rounded-xl p-8">
      <h3 className="text-xl font-bold text-white mb-2">Personal Coach Summary</h3>
      <p className="text-sm text-muted leading-relaxed">
        Readiness status: <span className={cn('font-bold border-b-2', readinessBand.tone, readinessBand.tone.replace('text-', 'border-'))}>{readinessBand.label}</span>. {readinessBand.note}
      </p>
      <div className="mt-6 rounded-2xl border border-primary/20 bg-primary/5 p-5 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-4 opacity-5">
          <Sparkles className="w-20 h-20 text-primary" />
        </div>
        <p className="text-[10px] uppercase font-black tracking-widest text-primary mb-2">Next Best Action</p>
        <p className="text-lg font-bold text-white leading-tight pr-10">{nextBestAction}</p>
      </div>
    </div>
  )
}
