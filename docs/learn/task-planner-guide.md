# Task Planner v2: how it works (study guide)

Read this with the code open. Goal: you can explain any part of the planner, and why it was built that way, in an
interview. Research and plan: [the planner plan](../plans/2026-11-25-task-planner-plan.md).

---

## 1. The 60-second pitch

> "The planner turns a five-step questionnaire into a dated study plan:
> - **The questions:** your level, role, company type, college year, language, and weekday and weekend hours.
> - **The subjects:** DSA, OS, DBMS, networks, OOP, low- and high-level design, projects, and aptitude when you
>   target service companies.
>
> The key decision: **the schedule is built by code, not by the LLM.** Research on LLM planning (TravelPlanner)
> shows models meet all the constraints of a multi-constraint plan less than 1% of the time. So a deterministic
> scheduler owns dates, hours, prerequisites and spaced reviews, and property tests prove it never overfills a day
> or breaks a prerequisite. The LLM writes only the roadmap explanation and project ideas, and code checks those
> too.
>
> It's honest about time. It plans with 85% of the hours you state (people underestimate their own tasks), tells
> you when the goal doesn't fit and what would fit, and after two weekly check-ins plans with your *real*
> completion rate. Mock-interview results and resume gaps feed back in as priorities. Eight sample users are
> checked in CI."

## 2. The pipeline

```
PlannerProfile (questionnaire)                      schemas.py
  -> select_topics()   which topics, how many minutes  selection.py
  -> build_calendar()  usable minutes per day          capacity.py
  -> top_ups()         spare time -> extra practice    builder.py
  -> fit()             cut nice/should topics if short capacity.py
  -> build_schedule()  dated tasks + roadmap           scheduler.py
  -> stored: plans, plan_topics, 14 days of plan_tasks service.py
```
`builder.py` joins the pure steps. Preview, create, every re-plan and the persona eval all call it.

## 3. Personalisation (selection.py)

| Answer | Effect |
|---|---|
| Level + company type | Subject mix from `curriculum/weights.yaml` (e.g. entry/product: DSA 40%; senior: HLD 30%) |
| College year 1-2 | Their own mix: foundations first, no OS/CN yet, no aptitude |
| Self-rating 0-4 | Topic minutes × 1.0 / 0.8 / 0.55 / 0.3 / 0.15 |
| Interview score < 60 or a matching gap | Factor never below 0.55, and the topic's priority goes up (evidence beats self-rating) |
| Language + comfort ≤ 2 | Tasks say "in Python"; adds a "Python for DSA" module |
| Problems solved | Fewer minutes per problem as you get experienced |
| Projects | "Build" track (scope → core → tests → deploy → write-up) or "deepen" track |
| Target role | Small role add-on (APIs for backend, React for frontend, statistics for data) |
| Degree BCA / B.Sc | CS subjects × 1.2 |

The curriculum is YAML (`backend/app/planner/curriculum/`). `curriculum.py` checks it at load time: ids are
unique, prerequisites exist, and there are no prerequisite cycles (a depth-first search).

## 4. Time and feasibility (capacity.py)

- **Usable minutes per day** = your hours × 0.85, with 0 on your rest day and busy dates.
- **Final window:** the last ~15% of days (7-21) are kept for revision and mocks.
- **Demand per topic** = minutes left plus its spaced reviews (3 × 15 min). Counting the reviews was a real bug the
  property tests caught: reviews took ~20 hours that the fit check ignored.
- **If demand > capacity:** cut extra-practice top-ups first, then nice-to-have topics, then should-have ones (lowest
  subject weight first). Must-haves and checkpoints are never cut. The plan then says what it cut and gives a
  suggestion like "add about 3 hours per week, or move your date to 14 Mar".
- **If there's spare time:** practice-heavy subjects (DSA, aptitude, mocks, LLD, HLD) get "extra practice" topics,
  split by how far each is below its share. The persona eval caught that aptitude was stuck at 14% (its weight is
  25%) without this.

## 5. The scheduler (scheduler.py): explain this one well

For each day, in order:
1. **Reviews due** (+2, +7, +21 days after a topic finishes), 15 minutes each, at most 20% of the day. This follows
   the spacing research (Cepeda et al. 2008).
2. **Learning sessions until the day is full.** The next subject is the one **furthest behind its share**:
   `deficit = weight × minutes scheduled so far − minutes this subject got`. This is weighted fair queueing:
   subjects interleave instead of running in blocks, and the mix converges to the weights. A topic starts only once
   its prerequisites are finished. Long subjects (projects, LLD, HLD) wait for weekends when anything else is
   available.
3. **Revision and mock templates** once all learning is placed, or once the final window starts.

It's deterministic: the same input gives the same plan (tested). Phases (Foundation, Core, Advanced, Final) and
weekly milestones are computed from the schedule afterwards, so they always match it.

## 6. Adaptation (service.py)

There is one re-plan function, `refresh()`:
- Tasks from earlier days that were never done are marked **missed** and kept as history.
- Every unfinished task from today on is deleted; moved ("pinned") tasks stay and their time is reserved.
- The scheduler re-runs from today with the real progress. Missed work is still "remaining" on its topic, so it
  comes back.
- The next 14 days are stored.

It runs when you open the planner after missing tasks, when fewer than 7 days of tasks remain, weekly, after a
check-in, and on "Re-plan". The **check-in** sets `capacity_factor = 0.85 × average completion rate of the last two
weeks` (kept between 0.4 and 0.85); "too hard" adds 15% per problem. **Interviews** completed after the plan started
add a "re-learn" topic when a CS score is < 60, and close interview gaps when it's ≥ 75.

## 7. Where the LLM is used (text.py)

| Output | Checks before it is shown | Fallback |
|---|---|---|
| Roadmap summary | No digits (numbers come from code); no subjects that aren't in the plan; phase names must match | Template text |
| Project ideas | Tech must be from your stack, resume skills, gaps or the role list; no duplicates of resume projects | No ideas shown |

Both run in a background task after the plan is created; the plan never waits for them.

## 8. Testing

- `tests/planner/test_core.py`:
  - personalisation rules
  - calendar, feasibility and cuts
  - **scheduler properties** over many profiles: never over capacity, nothing on rest/busy days, prerequisites
    first, reviews at the right offsets, everything scheduled when "fits"
  - determinism and re-planning
- `tests/planner/test_planner_api.py`: create, archive, done/undo, missed tasks re-planned, pinned moves,
  check-in, interview ingestion, suggestions, ownership.
- `evals/planner/run.py`: 8 personas with expected subject shares and feasibility, in CI.

## 9. Interview questions you might get

- *Why not let the LLM make the schedule?* → Multi-constraint planning is where LLMs fail (0.6% on TravelPlanner).
  LLM-Modulo research says to pair the LLM with verifiers; here code does the planning and the LLM only writes
  text, which is itself verified.
- *How do you keep the subject mix right?* → Deficit-based picking, the same idea as weighted fair queueing in
  networking.
- *What if the user falls behind?* → Missed tasks are kept as history, the work is re-planned, and check-ins shrink
  future capacity to the real completion rate.
- *How do you know it works?* → Property tests over 40+ generated profiles, plus a persona eval with expected
  shares.

## 10. Honest limitations

- Hour estimates per topic are my estimates; they're tuned by the check-in pace, not measured per user.
- Self-ratings are subjective until mock interviews provide evidence.
- Only CS subjects have interview checkpoints (DSA has no coding sandbox yet).
- Re-planning uses list-and-filter on tasks; fine at personal scale, would need indexed range queries at large scale.

## 11. File map

| File | What it does |
|---|---|
| `app/planner/curriculum/*.yaml` | Topics, minutes, prerequisites, suggested problems, resources, weights |
| `app/planner/curriculum.py` | Load + validate (ids, prerequisites, cycles, weights add to 100) |
| `app/planner/selection.py` | Which topics and how long (personalisation) |
| `app/planner/capacity.py` | Calendar, demand, fit/cut, suggestion |
| `app/planner/scheduler.py` | The day-by-day scheduler + roadmap |
| `app/planner/builder.py` | Joins the steps; extra-practice top-ups |
| `app/planner/service.py` | Persistence, refresh, tasks, check-ins, interview ingestion |
| `app/planner/text.py` | LLM summary + project ideas with checks |
| `frontend/src/features/planner/` | Wizard, week view, roadmap, progress, check-in, task rows |

## 12. Draft CV bullet

- "Built a personalised study planner: a 5-step profile (level, role, company type, college year, weekday/weekend
  hours) becomes a dated roadmap across DSA, CS fundamentals, LLD/HLD and projects via a deterministic scheduler with
  weighted fair interleaving and spaced reviews; property-tested to never exceed daily capacity or break
  prerequisites, and re-planned from real completion rates and mock-interview results."
