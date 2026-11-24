/** Display names shared by the interview pages. */

export const TRACKS = {
  mixed: { label: 'Mixed campus round', hint: '2 project + 2 CS fundamentals + 1 HR, like a real campus technical round.' },
  resume: { label: 'Resume deep-dive', hint: 'Questions about your own projects and experience. Needs a resume.' },
  jd: { label: 'Job description', hint: 'Questions aimed at a saved JD’s must-have requirements.' },
  fundamentals: { label: 'CS fundamentals', hint: 'OS, DBMS, Computer Networks and OOP.' },
  behavioral: { label: 'HR / behavioral', hint: 'STAR questions: conflict, failure, ownership, deadlines.' },
} as const

export type TrackKey = keyof typeof TRACKS

export const TOPICS = { os: 'OS', dbms: 'DBMS', cn: 'Computer Networks', oop: 'OOP' } as const
export type TopicKey = keyof typeof TOPICS

const TOPIC_DISPLAY: Record<string, string> = { ...TOPICS, behavioral: 'HR / behavioral', projects: 'Projects' }
export const topicLabel = (topic: string) => TOPIC_DISPLAY[topic] ?? topic

export const BANDS = {
  ready: { label: 'Ready', style: 'text-success' },
  almost: { label: 'Almost there', style: 'text-warning' },
  practice: { label: 'Needs practice', style: 'text-error' },
} as const

export const SCORE_FORMULA =
  'Each answer: 60% rubric (each dimension scored 1-5 against written descriptions; 1 = 0, 5 = 100) + ' +
  '40% coverage (key points covered, each backed by a quote from your answer). A follow-up can cover points ' +
  'you missed in the main answer. Skipped questions score 0. Session score = average of the questions.'
