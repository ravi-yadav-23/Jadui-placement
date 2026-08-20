# Jadui Placement — AI Career Coach

![Stack](https://img.shields.io/badge/Stack-Next.js%20|%20FastAPI%20|%20Supabase-blue?style=for-the-badge)
![AI](https://img.shields.io/badge/Engine-Gemini%20|%20Groq%20|%20Vapi-emerald?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Live-green?style=for-the-badge)

**Jadui Placement** is a full-stack, agentic AI career coaching platform that helps users close the gap between where they are and where top companies want them to be. It's not a dashboard — it's an end-to-end career intelligence system with voice interviews, resume AI, GitHub analytics, and a real-time readiness score.

🔗 **Live Demo:** [jadui-placement.vercel.app](https://jadui-placement.vercel.app)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Next.js 14 Frontend                │
│   14 pages  ·  Student Dashboard  ·  Admin Panel   │
└────────────────────────┬────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────┐
│              FastAPI Backend (Python)               │
│                                                     │
│  resume_ai  ·  interview_ai  ·  github_profile      │
│  github_review  ·  mentor_ai  ·  admin_ai           │
│  system_ai                                          │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│         Supabase  (PostgreSQL + Realtime)           │
└─────────────────────────────────────────────────────┘
```

---

## Key Features

### Student Dashboard
A career intelligence suite for serious job seekers.

- **Readiness Radar** — Real-time 4-axis score aggregating Resume Quality, Technical Depth (GitHub), Interview Performance, and Consistency into a single placement-readiness metric
- **AI Resume Intelligence** — Deep resume parsing via Groq, identifying strengths, gaps, and high-impact improvements with section-level feedback
- **Voice Interview Engine** — AI-driven mock interviews powered by Gemini + Vapi, with adaptive question generation based on target role and real-time per-answer scoring
- **GitHub Action Agent** — Automated PR review and technical bio generation derived from commit history and repository analysis
- **AI Mentor Chat** — Conversational career mentor with full dashboard context awareness
- **Weekly Roadmap** — AI-generated task planning and execution tracking

### Admin Panel
A control layer for managing users and platform insights.

- **Batch User Analytics** — Identify top performers and critical skill gaps across the entire user base at a glance
- **Candidate-to-Role Matching** — AI-driven simulation predicting user-to-job fit based on tech stack similarity
- **Workshop Clustering Agent** — Automatically groups users by shared skill gaps and proposes targeted learning sessions
- **Student Dossier** — Per-user deep-dive with AI-generated profile summaries and internal vetting notes

---

## Technology Stack

| Layer | Technology |
|:---|:---|
| **Frontend** | Next.js 14, Tailwind CSS, Radix UI, Recharts, Framer Motion |
| **Backend** | FastAPI (Python), Pydantic, Uvicorn |
| **Database** | Supabase (PostgreSQL + Realtime) |
| **AI — Resume** | Groq (fast inference, resume parsing) |
| **AI — Interviews** | Google Gemini (question generation + scoring), fallback to OpenAI |
| **AI — Voice** | Vapi (real-time voice interview sessions) |
| **Storage** | Cloudinary (resume file storage) |
| **Dev Tools** | GitHub REST API, Git |

---

## Module Breakdown

```
backend/
├── modules/
│   ├── resume_ai/        # PDF upload, Groq parsing, analysis, Supabase storage
│   ├── interview_ai/     # Gemini question generation, per-answer scoring, sessions
│   ├── github_profile/   # GitHub API aggregation with 6hr caching layer
│   ├── github_review/    # AI-powered PR review service
│   ├── mentor_ai/        # Conversational AI mentor
│   ├── admin_ai/         # Batch analytics, matching simulation, workshop agent
│   └── system_ai/        # Health, system-level routes

frontend/
├── app/
│   ├── dashboard/        # resume, interview, github-profile, chat, progress, tasks
│   ├── admin/            # main, students, workshops, login
│   └── auth/             # login, signup
```

---

## Getting Started

### Prerequisites
- Node.js 18+
- Python 3.11+
- Supabase project
- API Keys: `GEMINI_API_KEY`, `GROQ_API_KEY`, `VAPI_API_KEY`, `GITHUB_TOKEN`

### Environment Setup

Copy `.env.example` to `.env` in both `/backend` and `/frontend` and fill in your keys.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`. Health check: `GET /health`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

---

## Design

Deep Slate & Amber color system with glass-morphism cards, subtle micro-animations, and a premium dark mode — built for a polished experience across student and admin interfaces.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
