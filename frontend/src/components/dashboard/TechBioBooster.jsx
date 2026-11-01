import { Target, Sparkles, ArrowRight } from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'
import { useApp, ACTIONS } from '@/context/AppContext'
import { fetchWithAuth } from '@/lib/fetchWithAuth';

export default function TechBioBooster({ careerSuggestions, latestResumeId }) {
  const { dispatch } = useApp()
  const [syncingBooster, setSyncingBooster] = useState(null)

  const handleApplyBooster = async (boosterText, index) => {
    if (!latestResumeId) return
    
    setSyncingBooster(index)
    try {
      const res = await fetchWithAuth('/api/resume/result', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          result_id: latestResumeId,
          add_strengths: [boosterText]
        })
      })
      
      if (!res.ok) throw new Error('Failed to apply booster')
      
      const data = await res.json()
      
      dispatch({ 
        type: ACTIONS.SET_RESUME, 
        payload: data.result 
      })

      setSyncingBooster(-1)
      setTimeout(() => setSyncingBooster(null), 2000)
    } catch (err) {
      console.error('Booster application failed:', err)
      setSyncingBooster(null)
    }
  }

  return (
    <div className="glass border border-border rounded-2xl p-6 relative overflow-hidden group">
      <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
        <Sparkles className="w-16 h-16 text-primary" />
      </div>
      <h3 className="text-lg font-bold text-white mb-1">Technical Bio Booster</h3>
      <p className="text-xs text-muted mb-6">AI-generated resume bullets from GitHub</p>
      
      <div className="space-y-4">
        {careerSuggestions.length > 0 ? (
          careerSuggestions.map((sug, i) => (
            <div key={i} className="relative pl-4 border-l-2 border-primary/30 group/item flex justify-between items-start gap-4">
              <div className="absolute -left-[5px] top-1.5 w-2 h-2 rounded-full bg-primary/40 group-hover/item:bg-primary transition-colors" />
              <p className="text-sm text-muted group-hover/item:text-white transition-colors leading-relaxed">
                {sug}
              </p>
              <button 
                disabled={syncingBooster !== null || !latestResumeId}
                onClick={() => handleApplyBooster(sug, i)}
                className={cn(
                  "flex-shrink-0 text-[10px] font-bold uppercase py-1 px-2 rounded border transition-all",
                  syncingBooster === i ? "bg-primary/20 text-primary animate-pulse" : 
                  syncingBooster === -1 ? "bg-success/20 text-success border-success/30" :
                  "bg-surface border-border text-muted hover:text-white hover:border-primary/50"
                )}
              >
                {syncingBooster === i ? "Applying..." : syncingBooster === -1 ? "✓ Added" : "Add to Resume"}
              </button>
            </div>
          ))
        ) : (
          <div className="text-center py-8">
            <div className="w-12 h-12 rounded-full bg-surface/50 flex items-center justify-center mx-auto mb-3">
               <Target className="w-6 h-6 text-muted" />
            </div>
            <p className="text-xs text-muted italic">No technical boosters yet. Scan your GitHub profile to unlock.</p>
          </div>
        )}
      </div>
      
      <div className="mt-8 pt-4 border-t border-border/50">
         <button className="flex items-center gap-2 text-xs text-primary font-bold hover:gap-3 transition-all">
            Copy all to clipboard
            <ArrowRight className="w-3 h-3" />
         </button>
      </div>
    </div>
  )
}
