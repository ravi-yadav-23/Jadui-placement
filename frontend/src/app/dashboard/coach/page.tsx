'use client'

import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { ArrowUp, Check, Loader2, Trash2 } from 'lucide-react'

import { Button, Notice, PageHeader, Spinner, Textarea } from '@/components/ui'
import { useClearCoach, useCoachMessages, useSendMessage } from '@/features/coach/hooks'
import { useCreateInterview } from '@/features/interview/hooks'
import { useMoveTask, useReplan, useUpdateTask } from '@/features/planner/hooks'
import type { CoachAction, CoachMessage } from '@/lib/api/types'
import { cn } from '@/lib/utils'

const PAGES: Record<string, string> = {
  today: '/dashboard', planner: '/dashboard/planner', roadmap: '/dashboard/planner?tab=roadmap',
  interview: '/dashboard/interview', resume: '/dashboard/resume', settings: '/dashboard/settings',
}
const STARTERS = [
  'What should I focus on this week?',
  'How am I doing so far?',
  'I finished my first task today.',
  'Which topic should I practise in a mock interview?',
]

/** Chat with a coach that sees your plan, scores and gaps. Its suggestions are buttons; nothing runs until you click. */
export default function CoachPage() {
  const messages = useCoachMessages()
  const send = useSendMessage()
  const clear = useClearCoach()
  const [text, setText] = useState('')
  const end = useRef<HTMLDivElement>(null)

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })   // returns a Promise in newer browsers: don't return it
  }, [messages.data?.length, send.isPending])

  const submit = (content: string) => {
    const value = content.trim()
    if (!value || send.isPending) return
    send.mutate(value)
    setText('')
  }
  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit(text)
    }
  }
  const list = messages.data ?? []

  return (
    <div className="flex min-h-[calc(100vh-8rem)] flex-col">
      <PageHeader title="Coach" description="Ask about your plan, scores or what to do next. It only knows what's in this app."
        actions={list.length > 0 && (
          <Button variant="ghost" size="sm" onClick={() => confirm('Delete this conversation?') && clear.mutate()}>
            <Trash2 className="h-3.5 w-3.5" /> Clear
          </Button>
        )} />

      <div className="flex-1 space-y-5 pb-6" aria-live="polite">
        {messages.isLoading && <Spinner label="Loading…" />}
        {!messages.isLoading && list.length === 0 && (
          <div className="rounded-lg border border-dashed border-border p-6">
            <p className="font-medium">Start with a question</p>
            <p className="mt-1 text-sm text-fg-muted">The coach sees your plan, today&apos;s tasks, resume review, interview scores and gaps. When it suggests something (open a page, mark a task done, start a mock), you get a button; nothing happens until you click it.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {STARTERS.map((s) => (
                <button key={s} type="button" onClick={() => submit(s)}
                  className="rounded-full border border-border bg-surface px-3 py-1.5 text-sm hover:border-border-strong">{s}</button>
              ))}
            </div>
          </div>
        )}
        {list.map((m) => <Message key={m.id} message={m} />)}
        {send.isPending && (
          <p className="flex items-center gap-2 text-sm text-fg-muted"><Loader2 className="h-4 w-4 animate-spin" /> Thinking…</p>
        )}
        {send.error && <Notice>{send.error.message}</Notice>}
        <div ref={end} />
      </div>

      <form onSubmit={(e: FormEvent) => { e.preventDefault(); submit(text) }}
        className="sticky bottom-0 -mx-1 border-t border-border bg-bg px-1 pb-2 pt-3">
        <div className="relative">
          <Textarea rows={2} value={text} onChange={(e) => setText(e.target.value)} onKeyDown={onKey} maxLength={2000}
            placeholder="Ask the coach… (Enter to send, Shift+Enter for a new line)" className="resize-none pr-12" aria-label="Message" data-testid="coach-input" />
          <Button type="submit" size="sm" className="absolute bottom-2 right-2 h-8 w-8 p-0" disabled={!text.trim() || send.isPending} aria-label="Send">
            <ArrowUp className="h-4 w-4" />
          </Button>
        </div>
      </form>
    </div>
  )
}

function Message({ message }: { message: CoachMessage }) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <p className="max-w-[80%] whitespace-pre-wrap rounded-lg bg-subtle px-3.5 py-2.5 text-sm">{message.content}</p>
      </div>
    )
  }
  return (
    <div className="max-w-[85%]" data-testid="coach-reply">
      <p className="mb-1 text-xs font-medium text-fg-subtle">Coach</p>
      <div className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</div>
      {!!message.actions?.length && (
        <div className="mt-3 flex flex-wrap gap-2">{message.actions.map((a, i) => <ActionButton key={i} action={a} />)}</div>
      )}
    </div>
  )
}

/** Runs a proposed action through the normal API, only when clicked. */
function ActionButton({ action }: { action: CoachAction }) {
  const router = useRouter()
  const update = useUpdateTask()
  const move = useMoveTask()
  const replan = useReplan()
  const interview = useCreateInterview()
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const busy = update.isPending || move.isPending || replan.isPending || interview.isPending

  const run = () => {
    const ok = () => setDone(true)
    const fail = (e: Error) => setError(e.message)
    switch (action.type) {
      case 'open_page': return router.push(PAGES[action.page ?? 'today'])
      case 'mark_task_done': return update.mutate({ id: action.task_id!, status: 'done' }, { onSuccess: ok, onError: fail })
      case 'move_task': return move.mutate({ id: action.task_id!, date: action.date! }, { onSuccess: ok, onError: fail })
      case 'replan': return replan.mutate(undefined, { onSuccess: ok, onError: fail })
      case 'start_interview':
        return interview.mutate({ track: action.track ?? 'fundamentals', mode: 'practice', question_count: 5, difficulty: 'any',
          topics: action.topics?.length ? action.topics : ['os', 'dbms', 'cn', 'oop'] },
        { onSuccess: (data) => router.push(`/dashboard/interview/${data.id}`), onError: fail })
    }
  }
  return (
    <span className="inline-flex flex-col">
      <Button variant="secondary" size="sm" onClick={run} loading={busy} disabled={done} data-testid="coach-action"
        className={cn(done && 'text-success')}>
        {done && <Check className="h-3.5 w-3.5" />} {action.label}
      </Button>
      {error && <span className="mt-1 text-xs text-danger">{error}</span>}
    </span>
  )
}
