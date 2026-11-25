/** Display names for planner data. */

export const SUBJECTS: Record<string, string> = {
  dsa: 'DSA', os: 'OS', dbms: 'DBMS', cn: 'Networks', oop: 'OOP', lld: 'LLD', hld: 'System design',
  projects: 'Projects', aptitude: 'Aptitude', practice: 'Interview practice', role: 'Role skills',
}
export const subjectLabel = (s: string) => SUBJECTS[s] ?? s

export const KINDS: Record<string, string> = {
  learn: 'Learn', practice: 'Practice', review: 'Review', project: 'Project', mock: 'Mock interview', checkpoint: 'Checkpoint',
}

export const PHASE_HINT: Record<string, string> = {
  Foundation: 'Prerequisites and basics',
  Core: 'Main topics, all subjects interleaved',
  Advanced: 'Harder patterns, design, project polish',
  'Final revision and mocks': 'No new topics: timed practice and mocks',
}

export const LANGUAGES = { cpp: 'C++', java: 'Java', python: 'Python', javascript: 'JavaScript', go: 'Go' } as const
export const ROLES = {
  sde: { label: 'SDE (general)', hint: 'Software engineer, any team' },
  backend: { label: 'Backend', hint: 'APIs, databases, services' },
  frontend: { label: 'Frontend', hint: 'Web UI, React, performance' },
  fullstack: { label: 'Full-stack', hint: 'Both sides of a web app' },
  data: { label: 'Data / ML', hint: 'Data engineering, analytics, ML' },
} as const
export const COMPANIES = {
  service: { label: 'Service-based', hint: 'TCS, Infosys, Wipro… aptitude + fundamentals' },
  product: { label: 'Product / startups', hint: 'DSA rounds, projects, fundamentals' },
  top_product: { label: 'Top product', hint: 'FAANG-level: harder DSA, early LLD' },
} as const
export const RATING_SUBJECTS = [
  ['dsa', 'DSA'], ['os', 'Operating systems'], ['dbms', 'DBMS'], ['cn', 'Computer networks'], ['oop', 'OOP'],
  ['system_design', 'System design'], ['aptitude', 'Aptitude'],
] as const
export const RATING_LABELS = ['Never studied', 'Basics', 'Okay', 'Good', 'Strong']
