'use client'

import { useCallback, useEffect, useState } from 'react'
import { Mic, MicOff, Send, Volume2 } from 'lucide-react'

import type { AnswerRequest } from '@/lib/api/types'
import { cn } from '@/lib/utils'
import { useSpeechInput } from '../useSpeechInput'

const MAX_CHARS = 6000 // same limit as the backend (INTERVIEW_MAX_ANSWER_CHARS)

/** The current question + answer box. Voice fills the same text box, so you can fix it before sending. */
export default function AnswerBox({ question, turnKey, busy, onSubmit }: {
  question: string
  turnKey: string                      // changes when a new question appears: resets the box
  busy: boolean
  onSubmit: (body: AnswerRequest) => void
}) {
  const [text, setText] = useState('')
  const [usedVoice, setUsedVoice] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [readAloud, setReadAloud] = useState(false)
  const onVoiceText = useCallback((t: string) => setText(t), [])
  const speech = useSpeechInput(onVoiceText)
  const { reset: resetSpeech, stop: stopSpeech } = speech

  // New question: clear the box, restart the timer, optionally read the question out.
  useEffect(() => {
    setText('')
    setUsedVoice(false)
    setSeconds(0)
    resetSpeech()
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000)
    return () => { clearInterval(timer); stopSpeech() }
  }, [turnKey, resetSpeech, stopSpeech])

  useEffect(() => {
    if (!readAloud || typeof window === 'undefined' || !window.speechSynthesis) return
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(question))
  }, [question, readAloud])

  const toggleMic = () => {
    if (speech.listening) return speech.stop()
    setUsedVoice(true)
    speech.start(text)
  }

  const submit = () => {
    speech.stop()
    onSubmit({
      answer: text.trim(),
      answer_mode: usedVoice ? 'voice' : 'text',
      duration_seconds: usedVoice ? speech.spokenSeconds() : seconds,
    })
  }

  return (
    <section className="card-base space-y-4">
      <div className="flex items-start justify-between gap-4">
        <p className="text-lg font-medium leading-relaxed text-white" data-testid="question">{question}</p>
        <button title="Read questions aloud" onClick={() => setReadAloud((v) => !v)}
          className={cn('shrink-0 rounded-lg border p-2', readAloud ? 'border-primary text-primary' : 'border-border text-muted')}>
          <Volume2 className="h-4 w-4" />
        </button>
      </div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        maxLength={MAX_CHARS}
        rows={7}
        disabled={busy}
        placeholder="Answer as you would in the interview. Explain your reasoning, give an example."
        className="w-full rounded-lg border border-border bg-surface p-3 text-sm text-white placeholder:text-muted focus:border-primary focus:outline-none"
        data-testid="answer-box"
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 text-xs text-muted">
          <span>{Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, '0')}</span>
          <span>{text.trim() ? text.trim().split(/\s+/).length : 0} words</span>
          {speech.supported && (
            <button onClick={toggleMic} disabled={busy}
              className={cn('flex items-center gap-1 rounded-lg border px-3 py-1.5',
                speech.listening ? 'border-error text-error' : 'border-border text-white hover:border-primary')}>
              {speech.listening ? <><MicOff className="h-4 w-4" /> Stop</> : <><Mic className="h-4 w-4" /> Speak</>}
            </button>
          )}
        </div>
        <button onClick={submit} disabled={busy || !text.trim()}
          className="btn-primary flex items-center gap-2 disabled:opacity-50" data-testid="submit-answer">
          <Send className="h-4 w-4" /> Submit answer
        </button>
      </div>
      {speech.supported && (
        <p className="text-xs text-muted">Voice uses your browser’s speech service; check the text before submitting.</p>
      )}
    </section>
  )
}
