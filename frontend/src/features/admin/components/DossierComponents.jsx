'use client'

import { useState } from 'react'
import { Zap } from 'lucide-react'
import { fetchWithAuth } from '@/lib/fetchWithAuth'

export function TPONotes({ studentId, initialNotes }) {
  const [notes, setNotes] = useState(initialNotes || '')
  const [isSaving, setIsSaving] = useState(false)

  const handleSave = async () => {
    setIsSaving(true)
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    try {
      await fetchWithAuth(`${backendUrl}/api/admin/students/${studentId}/notes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes })
      })
    } catch { /* error */ }
    setIsSaving(false)
  }

  return (
    <div className="pt-10 border-t border-neutral-800 space-y-4">
       <div className="flex items-center justify-between">
          <h4 className="text-[10px] font-black uppercase tracking-widest text-neutral-500">Internal TPO Remarks</h4>
          <button 
            onClick={handleSave} 
            disabled={isSaving}
            className="text-[10px] font-black text-amber-500 uppercase hover:underline"
          >
            {isSaving ? 'Saving...' : 'Save Notes'}
          </button>
       </div>
       <textarea 
         value={notes}
         onChange={(e) => setNotes(e.target.value)}
         placeholder="Enter private observations (FAANG potential, soft-skill gaps, etc.)"
         className="w-full h-32 bg-neutral-900 border border-neutral-800 rounded-2xl p-4 text-xs text-neutral-400 outline-none focus:border-amber-500/30 font-medium resize-none"
       />
       <p className="text-[10px] text-neutral-600 italic">⚠️ These notes are private and NOT visible to the student.</p>
    </div>
  )
}

export function Section({ title, icon: Icon, children }) {
  return (
    <div className="space-y-4">
       <h4 className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.2em] text-neutral-600">
          <Icon className="w-4 h-4" /> {title}
       </h4>
       {children}
    </div>
  )
}

export function NoData() {
  return <p className="text-xs text-neutral-600 italic">No data synced for this student yet.</p>
}

export function Intervention({ studentId }) {
  const [taskText, setTaskText] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const handleAssign = async () => {
    if (!taskText) return
    setLoading(true)
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    try {
      const res = await fetchWithAuth(`${backendUrl}/api/admin/intervene/task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: studentId, title: taskText })
      })
      if (res.ok) {
        setSuccess(true)
        setTaskText('')
        setTimeout(() => setSuccess(false), 3000)
      }
    } catch { /* error handling */ }
    setLoading(false)
  }

  return (
    <div className="pt-6 border-t border-neutral-800 space-y-4">
       <h4 className="text-xs font-black uppercase text-amber-500 flex items-center gap-2">
         <Zap className="w-4 h-4 fill-amber-500" /> Mission Control: Inject Task
       </h4>
       <div className="flex gap-2">
          <input 
            value={taskText}
            onChange={(e) => setTaskText(e.target.value)}
            disabled={loading}
            placeholder="e.g. Redo System Design Mock Interview"
            className="flex-1 bg-neutral-800 border border-white/5 rounded-xl px-4 py-2 text-xs outline-none focus:border-amber-500/50"
          />
          <button 
            onClick={handleAssign}
            disabled={loading || !taskText}
            className="px-4 py-2 bg-amber-500 text-neutral-950 text-[10px] font-black uppercase rounded-xl disabled:opacity-50"
          >
            {loading ? '...' : (success ? 'Sent!' : 'Assign')}
          </button>
       </div>
    </div>
  )
}
