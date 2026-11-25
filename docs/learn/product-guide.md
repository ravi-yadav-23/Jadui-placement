# Dashboard, coach and the UI system (study guide)

How the pieces that tie the product together work: the Today dashboard, the coach chat, auth, and the design
system. Plan: [product v1 plan](../plans/2026-11-26-product-v1-plan.md).

---

## 1. Today dashboard (`backend/app/dashboard/service.py`)

One read-only endpoint, `GET /api/v2/dashboard`, built from the other pillars' summaries.

**Readiness** is a weighted mean of only the parts that have data. It needs at least two parts, so one data point
never pretends to be a verdict.

| Part | Value | Weight |
|---|---|---|
| Resume | latest general review score | 25 |
| Interviews | average of the last 3 mock interviews | 35 |
| Study plan | % of planned minutes done in the last 14 days | 25 |
| Gaps closed | closed ÷ all skill gaps | 15 |

Each part shows its value and where it comes from, and the formula is one click away. This replaces the old
dashboard's "readiness", which was computed from usage counts and fake defaults.

**Next actions** are plain rules (no LLM): finish today's tasks → weekly check-in → create a plan → upload or
review your resume → take a mock interview if none in 7 days. The **setup checklist** shows until the four first
steps are done; research on first-use empty states says they should drive one action.

## 2. Coach (`backend/app/coach/`)

```
POST /coach/messages {content}
  -> build_context(): JSON snapshot of profile, plan (today + 7 days of tasks WITH ids), milestones,
                      readiness, gaps, latest resume review actions, latest interview
  -> one LLM call (coach.v1) -> CoachDraft {reply, actions[0-3]}
  -> valid_actions(): drop any action that isn't backed by the context
  -> store question + reply; return the reply with its action buttons
```

**Why it's safe (OWASP LLM06 "Excessive Agency"):**
- **Limited tools:** five action types only (open a page, start an interview, mark a task done, move a task,
  re-plan).
- **No authority of its own:** the coach can't write anything. Each action is a button; clicking it calls the
  normal, authorised API.
- **Validation in code:** task ids must be in the context and still to do; dates must be between today and the
  target; tracks and topics come from fixed lists. The fake LLM in the tests deliberately proposes an invented task
  id, and the test checks it's dropped.
- **Grounding:** the prompt says facts about the student must come from the context; the test checks the reply
  names the real next task.
- **Limits:** 60 messages a day; the student's message is delimited as data.

## 3. Auth

- `AuthProvider` wraps Supabase Auth: it reads the session and listens for changes in other tabs and for token
  refresh.
- The dashboard shell redirects to `/auth/login?next=…` without a session.
- The backend verifies the JWT on every request (HS256 secret or the project's JWKS).
- There is **no demo login** any more (the old one let anyone in as "Alex Johnson").
- The Playwright run uses a test token that the build bakes in (`NEXT_PUBLIC_E2E_ACCESS_TOKEN`); a real deployment
  never sets it.
- Settings → "Delete my data" removes every row and file the user owns (`DELETE /api/v2/me/data`).

## 4. The design system (`frontend/src/app/globals.css`, `src/components/ui`)

- **Why it changed:** the old UI was the default "AI-generated" look (indigo/violet gradients, glow, glass, emoji).
  Writers who analyse that look point to stacked defaults and no design direction.
- **The direction:** neutral zinc greys, one jade accent (fits the name), Inter, 1 px borders, small radii, no
  gradients or glow. Density like daily-use tools.
- **Tokens:** CSS variables (RGB triplets) for light and dark. Tailwind maps names like `bg`, `surface`, `fg`,
  `fg-muted`, `primary` and `danger` to them, so every component switches theme without `dark:` classes.
- **Accessibility:** every text/background pair was computed to pass WCAG AA 4.5:1; input borders and focus rings
  were darkened to pass 3:1 (the first pick, 1.5:1, failed and was fixed).
- **Charts:** only bars and a sparkline. NN/g: position and length are the strongest encodings; colour only for
  status.
- **Components:** written in-house, no component library: Button, Card, Badge, form controls, Tabs, Segmented,
  Dialog (native `<dialog>`, so focus trap and Esc come for free), Progress, Sparkline, EmptyState.
- **Theme without a flash:** a tiny inline script sets the `dark` class before React loads.

## 5. The landing page (`frontend/src/features/landing/`)

- **Why no video:** the "how it works" demos are scripted React components, not screen recordings. They use the
  same markup and tokens as the app, so they stay sharp at any size, switch with the theme and weigh almost
  nothing. Update them by hand when the real screens change.
- **How a scene plays:** `useSteps(count, ms, playing)` is a timer that counts 0 → `count`. Each element shows when
  the step reaches its number (`<Reveal show={step >= 3}>`), and hidden elements keep their space so nothing jumps.
- **The player (`Walkthrough.tsx`):** six chapters (questionnaire, scheduler, interview, resume, coach, re-planning).
  A CSS progress bar under the active chapter runs for the chapter's length; its `animationend` moves to the next.
  It pauses off-screen (IntersectionObserver), on hover and with a Pause button (WCAG 2.2.2: moving content needs
  a pause control).
- **Reduced motion:** with the OS setting on, every scene shows its final state and nothing auto-advances; a global
  CSS rule also stops transitions.
- **Honest numbers:** every figure on the page is real (52 questions, 16 parse checks, reviews at 2/7/21 days,
  8 personas, the scoring and capacity formulas). The "Who it's for" bars come from
  `backend/app/planner/curriculum/weights.yaml`; keep them in sync if the weights change.
- **Test:** `e2e/landing.spec.ts` switches chapters, pauses, and checks the page is no wider than a phone (a grid
  without `min-w-0` once let the chapter strip stretch the page to 1,200 px).

## 6. Bugs worth telling as stories

- **A browser change broke an effect.** `useEffect(() => el.scrollIntoView({behavior: 'smooth'}))` crashed the coach
  page: newer Chrome returns a Promise from smooth `scrollIntoView`, and React tried to call it as the cleanup
  function. Fix: braces, so the effect returns nothing. Every expression-bodied effect was changed the same way.
- **Optimistic checkboxes.** Task checkboxes waited for the server, so they felt laggy (and Playwright's `check()`
  failed). Now the status updates immediately and rolls back on error.

## 7. File map

| Area | Files |
|---|---|
| Dashboard | `backend/app/dashboard/{service,schemas,api,account}.py`, `frontend/src/app/dashboard/page.tsx` |
| Coach | `backend/app/coach/*`, `backend/app/llm/prompts/coach.v1.md`, `frontend/src/app/dashboard/coach/page.tsx` |
| Auth | `frontend/src/features/auth/*`, `frontend/src/app/auth/*`, `backend/app/core/auth.py` |
| Shell + UI kit | `frontend/src/components/shell/*`, `frontend/src/components/ui/*`, `frontend/src/app/globals.css`, `tailwind.config.js` |
| Landing | `frontend/src/app/page.tsx`, `frontend/src/features/landing/*` |
| E2E | `frontend/e2e/{resume,interview,planner,landing}.spec.ts` |
