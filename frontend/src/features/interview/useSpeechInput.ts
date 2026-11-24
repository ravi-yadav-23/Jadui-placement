/**
 * Voice input with the browser's built-in speech recognition (Web Speech API).
 *
 * Free, but only in some browsers (Chrome/Edge; partial in Safari; not in Firefox by default),
 * so `supported` is false elsewhere and the mic button is hidden. The browser sends the audio to
 * its own speech service; we only ever receive text. The transcript goes into the normal answer
 * box, so the student can fix recognition mistakes before sending.
 */
import { useCallback, useEffect, useRef, useState } from 'react'

// Minimal types: TypeScript's DOM library does not include the Web Speech recognition API.
interface RecognitionResult { isFinal: boolean; 0: { transcript: string } }
interface RecognitionEvent { resultIndex: number; results: ArrayLike<RecognitionResult> }
interface Recognition {
  continuous: boolean
  interimResults: boolean
  lang: string
  onresult: ((event: RecognitionEvent) => void) | null
  onend: (() => void) | null
  start(): void
  stop(): void
}
type RecognitionConstructor = new () => Recognition

function recognitionClass(): RecognitionConstructor | null {
  if (typeof window === 'undefined') return null
  const w = window as unknown as { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null
}

/** `onText(text)` receives the full transcript so far (final + in-progress words) on every update. */
export function useSpeechInput(onText: (text: string) => void) {
  const [supported, setSupported] = useState(false)
  const [listening, setListening] = useState(false)
  const recognition = useRef<Recognition | null>(null)
  const startedAt = useRef<number | null>(null)
  const spokenMs = useRef(0) // total time the mic was on, for words-per-minute

  useEffect(() => setSupported(recognitionClass() !== null), [])
  useEffect(() => () => recognition.current?.stop(), [])

  const start = useCallback((existingText: string) => {
    const Recognition = recognitionClass()
    if (!Recognition) return
    const rec = new Recognition()
    rec.continuous = true
    rec.interimResults = true
    rec.lang = 'en-IN'
    let finalText = existingText ? `${existingText.trim()} ` : ''
    rec.onresult = (event) => {
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const piece = event.results[i][0].transcript
        if (event.results[i].isFinal) finalText += `${piece.trim()} `
        else interim += piece
      }
      onText((finalText + interim).trimStart())
    }
    rec.onend = () => {
      if (startedAt.current) spokenMs.current += Date.now() - startedAt.current
      startedAt.current = null
      setListening(false)
    }
    recognition.current = rec
    startedAt.current = Date.now()
    rec.start()
    setListening(true)
  }, [onText])

  const stop = useCallback(() => recognition.current?.stop(), [])

  /** Seconds the mic was on since the last reset (call reset when a new question appears). */
  const spokenSeconds = useCallback(() => {
    const running = startedAt.current ? Date.now() - startedAt.current : 0
    return Math.round((spokenMs.current + running) / 1000)
  }, [])
  const reset = useCallback(() => { spokenMs.current = 0 }, [])

  return { supported, listening, start, stop, spokenSeconds, reset }
}
