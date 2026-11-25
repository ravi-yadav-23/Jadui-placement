# Jadui Placement v1: product plan (UI rebuild, dashboard, coach, cleanup) — 2026-11-26

Status: **built (2026-11-26)**. Guide: [dashboard, coach and UI system](../learn/product-guide.md). The resume, interview and planner backends are done.
This plan covers everything else needed to ship it as one coherent product.

---

## 1. What is wrong today (audit)

| Area | Problem |
|---|---|
| Look and feel | Indigo/violet gradients, glow shadows, glassmorphism, animated gradient text, floating orbs, emoji icons: the default "AI-generated site" look. |
| Brand | Pages say "Agentic AI"; the product is Jadui Placement. |
| Auth | Login has a demo button that signs anyone in as "Alex Johnson" without Supabase; there's no guard on `/dashboard`; the legacy backend falls back to a shared demo user. |
| Dashboard / progress / tasks / chat | Built on the legacy `system_ai` and `mentor_ai` modules, a 230-line global `AppContext` saved to localStorage, derived or mock numbers, and a Next.js route that calls Gemini with a key on the frontend server. |
| Navigation | Two progress pages, a tasks page and a planner that don't share data; a notification bell with nothing behind it. |
| Consistency | The v2 pages (resume, interviews) reuse the old glowing cards, so they look like the rest. |

## 2. Research → design decisions

| Finding | Decision |
|---|---|
| The "AI look" is a stack of defaults (Tailwind indigo-500, purple gradients, glassmorphism, emoji, centred hero + three cards); what makes a product feel real is a clear design direction applied consistently ([DEV: blame indigo-500](https://dev.to/alanwest/why-every-ai-built-website-looks-the-same-blame-tailwinds-indigo-500-3h2p), [DEV: generic vs premium](https://dev.to/samareshdas/why-most-ai-generated-websites-still-feel-generic-and-what-actually-makes-a-product-feel-premium-33p2), [Built In](https://builtin.com/articles/ai-design-slop-era), [uxdesign.cc](https://uxdesign.cc/purple-6a6d1786f6c1)). | **Neutral, quiet UI with one accent.** Zinc greys, a single "jade" green accent (fits the name), Inter, 1 px borders, small radii, no gradients, glows, glass or emoji. Density like tools people use daily (Linear, GitHub), not a marketing page. |
| Dashboards should be read at a glance; **position and length** are the strongest encodings for quantities, colour is for flagging outliers ([NN/g: preattentive](https://www.nngroup.com/articles/dashboards-preattentive/), [NN/g video](https://www.nngroup.com/videos/data-visualizations-dashboards/)). | Bars and simple line sparklines only (no radar/donut charts). Colour only for status (on track / behind, weak topic). One headline number with its formula. |
| Text needs 4.5:1 contrast; UI components and focus indicators 3:1 ([W3C SC 1.4.3](https://w3.org/WAI/WCAG21/Understanding/contrast-minimum.html), [WebAIM](https://webaim.org/articles/contrast/)). | Token colours chosen to pass AA in light and dark themes; visible focus rings on every control. |
| The first-use empty state should **drive an action**, not just explain ([Smashing](https://smashingmagazine.com/2017/02/user-onboarding-empty-states-mobile-apps), [Userpilot](https://userpilot.com/blog/empty-state-saas/)). | A new user lands on "Today" with a short setup checklist (plan → resume → first interview); every empty state has one primary action. |
| OWASP LLM06 *Excessive Agency*: limit tools, scope permissions, and require **human approval** for actions; enforce authorisation outside the LLM ([OWASP](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/)). | The coach can only *propose* a small set of actions (open a page, start an interview, mark a task done, move a task, re-plan). Each appears as a button; nothing runs until you click, and the existing authorised APIs do the work. |

## 3. Information architecture

| Nav item | Route | What it is |
|---|---|---|
| Today | `/dashboard` | readiness (with formula), today's tasks, next actions, recent activity, setup checklist for new users |
| Planner | `/dashboard/planner` (+ `/setup`) | 5-step questionnaire, then Today/Week, Roadmap and Progress tabs, weekly check-in |
| Interviews | `/dashboard/interview` | v2 (restyled) |
| Resume | `/dashboard/resume` | v2 (restyled) |
| Coach | `/dashboard/coach` | chat grounded in your data, with proposed actions |
| Settings | `/dashboard/settings` | account, theme, study profile, delete my data |

Old routes (`/dashboard/tasks`, `/dashboard/progress`, `/dashboard/chat`) redirect to the new ones.

## 4. Backend additions

1. **Dashboard** (`app/dashboard`): `GET /api/v2/dashboard`, built from the other pillars' summaries.
   - **Readiness** = weighted mean of the parts that have data. Each part shows its value and a one-line explanation, and at least 2 parts are needed for a score:
     - resume: latest general review score, weight 25
     - interviews: average of the last 3, weight 35
     - plan: share of planned minutes done in the last 14 days, weight 25
     - gaps: share of gaps closed, weight 15
   - **Next actions:** rule-based, e.g. create a plan, upload a resume, run a review, practise an interview if none in 7 days, do the weekly check-in, finish today's tasks.
   - **Activity:** recent analyses, interviews, task days and plan changes.
2. **Coach** (`app/coach`): one conversation per user, stored in `coach_messages`.
   - **Context:** each message runs one LLM call (`coach.v1`, schema `CoachDraft`) with a server-built context: planner profile, today's tasks with ids, upcoming milestones, open gaps, latest resume review actions, latest interview result, readiness.
   - **Actions are validated:** task ids must be in the context, dates inside the plan, interview tracks and topics from the known lists; at most 3 per reply. The UI shows them as buttons.
   - **Limits:** 60 messages a day; "Clear conversation" deletes the history.
3. **Account**: `DELETE /api/v2/me/data` deletes every row the user owns in the v2 tables and their uploaded files.
4. **Remove legacy:**
   - backend: `modules/` (mentor, system), `app/shared`, the old `security.py` / `supabase_client.py`, `deployment/schema.sql`
   - frontend: every Next.js API route, `AppContext`, the legacy hooks/components/pages, and unused packages (`ai`, `@ai-sdk/google`, `framer-motion`, `recharts`, `class-variance-authority`)
   - The SQL to drop the legacy tables goes in the backlog (it deletes data, so you run it).

## 5. Frontend rebuild

- **Design tokens:** CSS variables for light and dark themes (system default, toggle in the user menu), in `globals.css` and Tailwind config.
- **Components** (`src/components/ui`): Button, Card, Badge, Input/Textarea/Select, Checkbox, Tabs, Progress, Stat, PageHeader, EmptyState, Skeleton, Dialog, SegmentedControl and Sparkline. They're small and written in-house, with no component library.
- **Auth:** `AuthProvider` wraps the Supabase session. The dashboard layout redirects to login without a session. Pages for login, signup, forgot password and set new password. No demo login; E2E uses its test token.
- **App shell:** a quiet sidebar with the wordmark, six nav items and the user menu (theme, settings, sign out); a slim header per page; a bottom nav on mobile.
- **Landing page:** an honest product page.
  - A real-looking preview of the Today screen, built from the actual components.
  - The four-part loop.
  - What makes each pillar trustworthy (truth guard, quote-verified judge, deterministic planner).
  - A "built with" section and a footer with GitHub.
  - No fake stats or testimonials.
- **Restyle the resume and interview pages** with the new components; **build** the planner, coach, Today and settings pages.

## 6. Quality

- Backend tests for the dashboard formula, coach action validation, data deletion, ownership.
- Playwright E2E:
  - the resume and interview flows, updated
  - **planner** (questionnaire → plan → tick a task)
  - **coach** (ask → reply → action button)
  - sign-in guard
- Screenshot review of every page, in light and dark themes.
- Docs: a planner study guide; coach and dashboard sections; README; backlog.
