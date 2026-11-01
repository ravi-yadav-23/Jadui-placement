export const ACTIONS = {
  SET_PROGRESS: 'SET_PROGRESS',
  SET_TASKS: 'SET_TASKS',
}

export function seedMockProgress(dispatch, actions = ACTIONS) {
  dispatch({
    type: actions.SET_PROGRESS,
    payload: {
      readinessScore: 72,
      taskCompletion: 58,
      interviewScore: 81,
      streak:         5,
      skillData: [
        { name: 'DSA',          level: 65 },
        { name: 'System Design',level: 48 },
        { name: 'React',        level: 82 },
        { name: 'Python',       level: 74 },
        { name: 'SQL',          level: 61 },
        { name: 'Communication',level: 78 },
      ],
    },
  })

  dispatch({
    type: actions.SET_TASKS,
    payload: [
      { id: '1', title: 'Solve 3 LeetCode Medium problems', category: 'DSA',     completed: true,  due: 'Today' },
      { id: '2', title: 'Complete System Design chapter 4',  category: 'Design',  completed: false, due: 'Today' },
      { id: '3', title: 'Mock interview — Behavioral round', category: 'Interview', completed: false, due: 'Today' },
      { id: '4', title: 'Build REST API with FastAPI',       category: 'Project', completed: true,  due: 'Yesterday' },
      { id: '5', title: 'Review DBMS concepts',              category: 'Core',    completed: false, due: 'Tomorrow' },
      { id: '6', title: 'Update LinkedIn profile summary',   category: 'Career',  completed: false, due: 'Tomorrow' },
    ],
  })
}
