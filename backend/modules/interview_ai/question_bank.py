class QuestionBank:
    def get_fallback_question_set(self, role_title: str) -> list[str]:
        rt = role_title.lower()
        if "frontend" in rt or "react" in rt:
            return [
                "How does React's reconciliation algorithm work under the hood?",
                "Explain the difference between useMemo and useCallback.",
                "How do you debug a severe memory leak in a single-page application?",
                "Describe a challenging UI performance issue you resolved.",
                "How would you architect the state management for a complex e-commerce app?",
            ]
        if "backend" in rt or "node" in rt or "python" in rt or "go" in rt:
            return [
                "How do you design a system to handle 10,000 concurrent websocket connections?",
                "Explain the trade-offs between SQL and NoSQL for a messaging app.",
                "How do you prevent race conditions in a distributed payment system?",
                "Describe a time you had to optimize a slow database query in production.",
                "How do you ensure idempotency in a REST API?",
            ]
        # General SWE fallback
        return [
            "Tell me about a time you had to deal with ambiguous requirements.",
            "Explain a complex technical concept to a non-technical stakeholder.",
            "How do you decide when to refactor code vs when to ship it?",
            "Describe the hardest bug you've ever had to debug.",
            "What is your approach to reviewing another engineer's code?",
        ]

question_bank = QuestionBank()
