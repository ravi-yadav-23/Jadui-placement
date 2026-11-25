# AI Goal-Based Task Planner v2: Research and Implementation Plan (2026-11-25)

Status: **built (2026-11-26)** with the recommended answers to §14. Additions found while building: spare time becomes
"extra practice" topics (the persona eval showed subjects with little content fell below their share), and missed
tasks are kept as history so check-ins can measure them. How it works: [the study guide](../learn/task-planner-guide.md).

Original status: draft for review. It reuses the foundation from the resume and interview
pillars (auth, data layer, LLM client, background jobs, test setup) and reads their outputs (`skill_gaps`,
resume profile, interview topic scores).

---

## 0. Summary

The planner asks you a short, **personal questionnaire** and turns the answers into a **full roadmap** to your
target date. The roadmap has phases and weekly milestones, and dated daily tasks sized to the time you actually have:
- **Subjects:** DSA, OS, DBMS, Computer Networks, OOP, projects, system design (LLD and HLD), and aptitude when you
  target service companies.
- **Personalized by:** your level (entry / 1-3 years / 3-5 years), role, company type, college year, preferred
  language, and hours per weekday and per weekend day.

```
questionnaire (+ what we already know: resume skills, resume/JD gaps, interview topic scores)
  -> curriculum selection (topics for your level, role, company type, year)
  -> demand (hours per topic, reduced by what you already know)
  -> capacity (your hours per day to the target date, minus a 15% buffer)
  -> feasibility check (fits? if not: what is cut, and what would make it fit)
  -> scheduler: phases -> weekly subject mix -> daily tasks (learn, practice, review, project, mock)
  -> you work through it; done / skipped / moved tasks, weekly check-in, new gaps -> re-plan
```

**The schedule is built by code; the LLM writes the personal parts.** Research shows LLMs fail at
multi-constraint planning (§1, finding 1). So hours, dates, prerequisites and spacing come from a deterministic,
tested scheduler. The LLM writes the roadmap explanation and tailored project ideas, and those are checked too.

What today's planner gets wrong:

| Today (`system_ai/services.py`, `features/tasks`) | v2 |
|---|---|
| A fixed 7-day template: "Practice {gap} for 60 minutes" × 3 per day, built from string formatting | A real curriculum (topics, prerequisites, hour estimates) scheduled into your calendar |
| Days 1-2 are always marked "done"; due dates are strings like "Today" / "This Week" | Real dates; nothing is marked done unless you do it |
| Ignores your time, level, role, year, language and deadline | All of these change the plan (§4) |
| No feasibility check: it never says the goal doesn't fit your time | Says what fits, what is cut, and how many extra hours or weeks would fit the rest |
| Tasks can't be undone, edited, moved or skipped; state saved as one JSON blob | Tasks are rows: done / skipped / moved; missed work rolls over and triggers a re-plan |
| Not connected to resume or interview results | Gaps from resume, JD match and interviews become prioritised topics; interview checkpoints test them |

**LLM calls per plan:** 0 for the schedule, 2 for the personal text (roadmap summary, project ideas). The
plan works without them: template text is used if the LLM fails.

---

## 1. Research findings -> design principles

| # | Finding | Design consequence |
|---|---------|--------------------|
| 1 | **LLMs can't reliably plan under many constraints.** On the TravelPlanner benchmark, GPT-4 met all constraints in **0.6%** of tasks ([Xie et al., ICML 2024](https://arxiv.org/html/2402.01622v4), [PMLR](https://proceedings.mlr.press/v235/xie24j.html)). The "LLM-Modulo" approach pairs the LLM with **external verifiers/solvers**: GPT-4o went from 8.3% to 23.9% on TravelPlanner, and every returned plan passed the critics ([Kambhampati et al.](https://arxiv.org/abs/2402.01817), [Gundawar et al.](https://arxiv.org/html/2411.14484v1)). | **A deterministic scheduler** owns hours, dates, prerequisites and spacing, and property tests verify it (never over capacity, prerequisites first, reviews spaced). The LLM only writes text, and what it writes is checked: topics it mentions must be in the plan; numbers come from code. |
| 2 | **Practice testing and distributed (spaced) practice** have the highest utility of ten study techniques; **interleaving** is moderate; rereading and highlighting are low ([Dunlosky et al. 2013](https://www.psychologicalscience.org/journals/pspi/1529100612453266/), [Duke](https://scholars.duke.edu/publication/954654)). | Tasks are **active**: solve problems, answer interview questions, explain a topic. Not "read chapter 3". Theory topics are **revisited** on a schedule, and **checkpoints** are mock interviews on that topic (the interview pillar = practice testing). Subjects are **interleaved** across the week instead of one subject for a month. |
| 3 | **The best review gap depends on how long you need to remember.** It's about 20-40% of the retention interval for a 1-week test and 5-10% for a 1-year test ([Cepeda et al. 2008](https://pubmed.ncbi.nlm.nih.gov/19076480/)). | Reviews at **+2, +7 and +21 days** after learning a topic: short sessions (15-20 min) that keep material fresh over a placement season measured in weeks to months. Reviews are capped at 20% of a day's time. |
| 4 | **Planning fallacy:** people underestimate how long their own tasks take. In Buehler et al.'s thesis study only ~30% finished within their own estimate ([Buehler, Griffin & Ross 1994](https://bear.warrington.ufl.edu/brenner/mar7588/Papers/buehler-et-al-1994.pdf), [summary](https://en.wikipedia.org/wiki/Planning_fallacy)). | Plan with **85% of the stated hours** (a 15% buffer kept as a weekly catch-up block). After two weeks, the weekly check-in measures your **real completion rate** and re-plans with it, so the plan follows what you actually do, not what you hoped. |
| 5 | **Implementation intentions** ("I will do X at time Y in place Z") raise goal attainment: d = 0.65 across 94 studies, with smaller effects in later domain-specific meta-analyses ([Gollwitzer & Sheeran 2006, via NCI](https://cancercontrol.cancer.gov/brp/research/constructs/implementation-intentions), [MCII meta-analysis](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2021.565202/pdf)). | Every task has a **date, a duration and a concrete action** ("Solve 3 sliding-window problems in Python, 60 min"), and the questionnaire asks **when** you study. Vague goals ("improve DSA") never appear as tasks. |
| 6 | **Coding-interview study plans are built from time left and hours per week**, with topics ordered by priority and weekly topic tables (arrays/strings/hashing first, then sorting, linked lists, stacks, then trees, graphs, heaps, tries). Practitioners stress planning around the hours you **really** have ([Tech Interview Handbook](https://www.techinterviewhandbook.org/coding-interview-study-plan/), [techinterview.org](https://www.techinterview.org/post/3233476075/coding-interview-study-plan-around-your-schedule/)). Popular sheets order DSA from basics to arrays, recursion, trees, graphs, DP and tries; Striver's A2Z lists 474 problems ([PracHub](https://prachub.com/resources/is-striver-s-a2z-dsa-sheet-enough-for-coding-interviews-in-2026), [Educative on NeetCode](https://www.educative.io/blog/neetcode-roadmap)). | The DSA curriculum is a **pattern-ordered topic graph** (arrays and hashing → two pointers → sliding window → stack → binary search → linked list → trees → heaps → backtracking → graphs → DP → tries), with problem counts scaled to your time and level, not a fixed 450-problem sheet. |
| 7 | **System design expectations depend on level:** new-grad loops often skip it or keep it to basic components and data flow; mid-level candidates drive requirements, APIs, schemas and a high-level design; seniors go deep on scale, failure modes and trade-offs ([Hello Interview](https://www.hellointerview.com/blog/the-system-design-interview-what-is-expected-at-each-level), [AlgoMaster](https://algomaster.io/learn/system-design-interviews/expectations-by-level), [Educative](https://www.educative.io/blog/senior-software-engineer-system-design-interview-questions)). In India, **machine-coding / LLD rounds** (Splitwise, parking lot, task scheduler; 90-120 min, running code, extensible classes) are common for SDE-1/SDE-2 at product companies ([LeetCode Flipkart SDE-2](https://leetcode.com/discuss/post/7560534/), [Blind Uber machine coding](https://www.teamblind.com/post/uber-india-machine-coding-90-minutes-iecvsdyw), [CodeChef guide](https://discuss.codechef.com/t/tutorial-how-to-prepare-for-machine-coding-round/38142)). | **Level decides the system-design share:** entry gets LLD basics and OOP design only; 1-3 years gets **LLD + machine coding** plus HLD basics; 3-5 years gets **deep HLD** plus LLD. |
| 8 | **Service vs product companies test differently** in India. Service firms use aptitude tests (e.g. TCS NQT) as the main filter, with fundamentals-level technical rounds. Product firms use aptitude only as a gate and **rank on DSA** (2-3 medium/hard problems in 90-120 min) after a resume screen ([GeeksforGeeks](https://www.geeksforgeeks.org/how-to-land-a-job-in-service-based-companies/), [FACE Prep](https://www.faceprep.in/article/placement-preparation-strategy-for-product-service-and-analytics-based-companies/), [Code360](https://www.naukri.com/code360/library/service-based-preparation), [PapersAdda](https://papersadda.com/article/service-vs-product-based-companies-2026/)). These are vendor blogs, so treat them as directional. | **Company type is a question**, and it changes the mix: service-based adds an **aptitude** subject and lowers DSA difficulty; product-based weights DSA highest; top product companies raise DSA difficulty and add LLD earlier. |

### Design principles
1. **Code schedules, the LLM writes.** Every date, hour and ordering comes from the scheduler; the LLM's text is
   validated against the plan.
2. **Plan for the real you.** 15% buffer at the start; after that, use your measured completion rate.
3. **Active tasks only.** Every task is something you *do* (solve, explain, build, answer), with a time box.
4. **Space and test.** Spaced reviews plus mock-interview checkpoints from the interview pillar.
5. **Honest feasibility.** If the goal doesn't fit your time, say so, show what was cut, and say what would fit.
6. **Ask only what changes the plan.** Every question in §2 maps to a rule in §4; if an answer wouldn't change the
   plan, we don't ask it.

---

## 2. The questionnaire (onboarding wizard)

Five short steps, about 2-3 minutes. Questions appear **only when relevant** (e.g. "year of study" only for
students; "years of experience" only for professionals). Anything we already know is **pre-filled** for you to
confirm.

### Step 1 · About you
| Question | Shown when | Options | Used for |
|---|---|---|---|
| Current status | always | College student · Graduate, looking for first job · Working professional | which questions follow; default level |
| Degree | student | B.Tech/BE · BCA · MCA · M.Tech · B.Sc · Other | whether CS subjects were taught (BCA/B.Sc get more fundamentals time) |
| Year of study | student | 1st · 2nd · 3rd · 4th (5th for dual degree) | intensity, horizon, subject mix (§4.3) |
| Expected graduation | student / graduate | month + year | default target date and eligibility |
| Goal | student | Internship · Full-time placement | target date default, difficulty |
| Years of experience | professional | number (0.5 steps) | default target level |
| Current role and tech stack | professional | text + skill chips | project and LLD examples; what to skip |

### Step 2 · Target
| Question | Shown when | Options | Used for |
|---|---|---|---|
| Target role | always | SDE (general) · Backend · Frontend · Full-stack · Data / ML | role add-on topics, project ideas |
| Target level | always (pre-filled) | Entry (0-1 yr) · Mid (1-3 yrs) · Senior (3-5 yrs) | subject weights, system-design depth |
| Company type (multi-select) | always | Service-based (TCS, Infosys, Wipro…) · Product / startups · Top product (FAANG-level) | aptitude, DSA difficulty, LLD timing |
| Target date | always | a date (placement drive / interview), or "no fixed date" | horizon (default by status and year, §4.3) |

### Step 3 · Time
| Question | Options | Used for |
|---|---|---|
| Hours per weekday | 0.5 - 8 (half-hour steps) | daily capacity Mon-Fri |
| Hours per weekend day | 0 - 10 | daily capacity Sat-Sun (weekends get projects, system design, mocks) |
| Rest day | none · Sat · Sun · any weekday | zero capacity that day |
| Busy dates | date ranges (exams, travel, festivals) | zero or reduced capacity |
| Usual study time | morning · afternoon · evening · night | shown on tasks ("Tonight, 60 min"); reminders later |

### Step 4 · Skills
| Question | Options | Used for |
|---|---|---|
| Preferred language for DSA | C++ · Java · Python · JavaScript · Go | language-specific tasks ("use `heapq`" vs "`PriorityQueue`") |
| Comfort with that language | 1 just started · 2 basics · 3 comfortable · 4 strong | adds a "language for DSA" module if ≤ 2 |
| Self-rating per subject | 0 never studied · 1 basics · 2 okay · 3 good · 4 strong; for DSA, OS, DBMS, CN, OOP, system design, aptitude (if service) | scales topic hours (§4.2) |
| Problems solved so far (any site) | 0 · <50 · 50-150 · 150-300 · 300+ | DSA starting point and difficulty |
| Projects | 0 · 1 · 2 · 3+, and "deployed / has users?" | project track: build first project vs deepen an existing one |

### Step 5 · What we already know (pre-filled, you confirm)
- **Resume:** skills and projects from your latest parsed resume (prefills Step 4 projects and stack).
- **Resume / JD gaps:** open `skill_gaps` from the screener, e.g. "Docker", "System design".
- **Interview scores:** topic averages from mock interviews, e.g. "OS 45, DBMS 72", which lower self-ratings
  that the evidence contradicts.
- Each item has a checkbox "include in my plan".

Answers are stored as a validated `PlannerProfile`. Editing the profile later triggers a re-plan that keeps
completed work.

---

## 3. Curriculum (the content model)

A reviewed YAML file per subject in `backend/app/planner/curriculum/`, the same pattern as the interview question bank.
You review it; it doubles as your own syllabus.

```yaml
- id: dsa.sliding_window
  subject: dsa
  title: Sliding window
  prerequisites: [dsa.arrays_hashing, dsa.two_pointers]
  learn_minutes: 60                  # first-time learning session(s)
  practice:                          # DSA only: problem counts by target difficulty
    problems: {service: 3, product: 6, top_product: 8}
    difficulty_mix: {easy: 0.3, medium: 0.6, hard: 0.1}
    suggested: ["Best Time to Buy and Sell Stock", "Longest Substring Without Repeating Characters",
                "Minimum Window Substring", "Sliding Window Maximum"]
  levels: [entry, mid, senior]
  priority: must                     # must | should | nice  (what gets cut first when time is short)
  checkpoint: null                   # theory topics link to an interview-bank topic instead
  resource: {title: "NeetCode: Sliding Window", url: "https://neetcode.io/roadmap"}
```

| Subject | Topics (first draft) | Notes |
|---|---|---|
| **DSA** | complexity & language setup, arrays & hashing, two pointers, sliding window, stack/monotonic stack, binary search, linked list, recursion, trees (traversals, BST), heaps, backtracking, graphs (BFS/DFS, topo sort, shortest paths), greedy, intervals, 1-D DP, 2-D DP, tries, bit manipulation | ~18 topics; problem minutes: easy 20, medium 40, hard 60 (adjusted by self-rating) |
| **OS** | processes & threads, scheduling, synchronization (mutex, semaphore, race conditions), deadlocks, memory & paging, virtual memory & replacement, file systems | checkpoints use the interview bank's `os` topic |
| **DBMS** | ER & keys, normalization, SQL (joins, group by, subqueries), indexing, transactions & ACID, isolation & concurrency, NoSQL & CAP basics | SQL topics get practice queries |
| **CN** | OSI/TCP-IP, TCP vs UDP & handshake, HTTP/HTTPS & TLS, DNS & "what happens when you type a URL", IP & subnetting, load balancing & caching basics | |
| **OOP** | four pillars, classes & interfaces, SOLID, design patterns (singleton, factory, strategy, observer), exceptions, UML basics | entry level stops here |
| **LLD** (mid+, top product entry) | modelling classes from requirements, design patterns in practice, concurrency basics, 6-8 machine-coding problems (parking lot, Splitwise, LRU cache, rate limiter, task scheduler, movie booking) | each problem is a 90-120 min timed build task + review |
| **HLD** (mid+) | scaling basics, load balancers, caching, databases & sharding, queues & async, consistency & CAP, then designs: URL shortener, rate limiter, chat, news feed, notification system | depth (number of designs) grows with level |
| **Projects** | milestones from the LLM project ideas (§7): scope → core feature → tests → deploy → write resume bullets | weekends; one project per ~6-8 weeks |
| **Aptitude** (service-based only) | quantitative, logical reasoning, verbal, timed mixed tests | only when service-based is chosen |
| **Interview practice** | HR/STAR stories, mock interviews (resume, fundamentals, mixed), final-phase full mocks | links into the interview pillar |
| **Role add-on** (small) | Frontend: JS deep-dive, browser rendering, React; Backend: REST/API design, auth, caching; Data/ML: statistics, ML basics, SQL analytics | ~10% of time; keeps the core subjects you asked for at the centre |

`curriculum.py` validates the files at startup (unique ids, prerequisites exist, no cycles, every subject has
topics for each level it claims). Tests fail on a bad edit.

---

## 4. Personalisation rules (every answer changes something)

### 4.1 Subject mix by level and company type (share of study time, %)
| Profile | DSA | CS fund. (OS+DBMS+CN+OOP) | LLD | HLD | Projects | Aptitude | Interview practice | Role add-on |
|---|---|---|---|---|---|---|---|---|
| Entry · service | 25 | 25 | – | – | 10 | 25 | 10 | 5 |
| Entry · product | 40 | 25 | 5 | – | 15 | – | 10 | 5 |
| Entry · top product | 45 | 20 | 10 | – | 10 | – | 10 | 5 |
| Mid (1-3 yrs) | 30 | 10 | 20 | 15 | 5 | – | 15 | 5 |
| Senior (3-5 yrs) | 20 | 5 | 15 | 30 | – | – | 25 | 5 |

- Several company types: the weights are averaged. These are **starting defaults** stored in
  `weights.yaml` and documented in the UI ("why is DSA 40%?").
- Interview practice for mid/senior includes behavioural and leadership stories (impact, conflict, ownership),
  because those rounds count more with experience.

### 4.2 Demand: how much time each topic needs
```
topic_minutes = (learn_minutes + practice_minutes) × knowledge_factor
knowledge_factor by self-rating (0-4): 1.0, 0.8, 0.55, 0.3, 0.15     (4 = review only)
practice_minutes (DSA) = Σ problems × minutes(difficulty)
```
- **Evidence overrides self-rating:** if an interview topic average is < 60, or a skill gap names the topic, the
  factor is at least 0.55 and the topic's priority goes up one level.
- **Language comfort ≤ 2** adds the "language for DSA" module (syntax, collections, I/O) in the first phase.
- **Problems solved:** 150+ skips the easy problems in early DSA topics; 300+ puts the mix at medium/hard.

### 4.3 College year and status (students)
| Year | Default horizon (no date) | Focus | Intensity note |
|---|---|---|---|
| 1st | 24 weeks | language + DSA foundations, OOP, one small project | warns above 2 h/day: consistency beats volume |
| 2nd | 20 weeks | DSA core, OOP, DBMS, first real project | internships next year |
| 3rd | 16 weeks, or until internship drive | DSA medium, all CS subjects, 2 projects, mocks | internship season |
| 4th / graduate | until placement date, else 12 weeks | full mix for target level, final-phase mocks | placement mode |
| Professional | 12 weeks | mix for target level; skip topics your stack covers (self-rating 4) | evenings/weekends realistic |

### 4.4 Other answers
| Answer | Effect |
|---|---|
| Degree BCA / B.Sc | CS-fundamentals topics × 1.2 (not all taught in the course) |
| Goal: internship | entry level, DSA medium cap, lighter HLD/LLD |
| Weekend hours | weekends get the long tasks: project milestones, machine coding, HLD designs, full mocks |
| Rest day / busy dates | zero capacity; tasks flow around them |
| Usual study time | shown on tasks; used for reminders later |
| Target role | role add-on topics; project ideas; LLD/HLD example systems (e.g. data → pipeline design) |
| Projects = 0 | the first project starts in week 1 (resumes need one); 2+ deployed → "deepen" milestones (tests, scale, write-up) |

---

## 5. The scheduler (deterministic, tested)

### 5.1 Capacity
```
for each day from start to target date:
    minutes = weekday_hours or weekend_hours (× 60); 0 on rest day / busy dates
usable = minutes × 0.85     # 15% buffer -> a weekly "catch-up" block on the lightest day
after 2 weekly check-ins: usable = minutes × clamp(completion_rate, 0.5, 1.0)
```

### 5.2 Feasibility
- `demand` = Σ topic minutes for selected topics, split by subject weights.
- **Fits:** demand ≤ capacity → extra capacity goes to more DSA problems, more mocks, then a second project.
- **Doesn't fit:** remove `nice` topics, then `should` topics, lowest weight first, until it fits. The result
  says: *"Your plan covers all must-have topics. Not included: tries, bit manipulation, HLD chat design. To include
  them: +4 h/week, or move your date to 14 March."* If even the `must` topics don't fit, it says so and suggests the
  smallest change that works (more hours or a later date).

### 5.3 Phases
| Phase | Share of time | Content |
|---|---|---|
| Foundation | ~20% | language module (if needed), prerequisites, first project scoped |
| Core | ~45% | main topics in prerequisite order, all subjects interleaved |
| Advanced | ~20% | hard DSA patterns, LLD/HLD designs, project polish |
| Final revision & mocks | ~15% (min 1 week) | spaced reviews, mixed mock interviews, weak-topic re-learn |

### 5.4 Weekly and daily packing
1. **Order** topics by prerequisites (topological sort), with ties broken by priority and subject weight.
2. **Weekly mix:** each week gets each subject's share of that week's minutes (§4.1); subjects are interleaved,
   not done in blocks.
3. **Daily pattern:**
   - **Weekdays:** a DSA session every day (daily consistency), plus one rotating theory subject (OS → DBMS → CN →
     OOP → …), plus any reviews due.
   - **Weekends:** long tasks (project milestone, LLD/HLD design, mock interview), plus the weekly catch-up block.
4. **Task sizes:** 25-90 minutes; a topic longer than that is split into sessions ("Paging 1/2", "Paging 2/2").
5. **Reviews:** after a topic's last learning session, add review tasks at +2, +7 and +21 days (15-20 min each);
   reviews never take more than 20% of a day.
6. **Checkpoints:** when a theory subject's topic group ends, add a short mock interview on that topic, linked to
   the interview pillar (fundamentals track with that topic preselected).
7. **Rolling horizon:** daily tasks are generated for the **next 14 days**. The rest of the roadmap is weekly
   milestones. Every Monday (or after any change), the next 14 days are rebuilt from the current state, so the
   detailed part always reflects what you actually did.

### 5.5 Properties the tests guarantee (for any profile)
- No day exceeds its capacity; rest days and busy dates have no tasks.
- No topic is scheduled before its prerequisites.
- Every `must` topic is scheduled whenever the plan reports "fits".
- Reviews fall on +2/+7/+21 days (or the next available day) and stay within 20% of a day.
- Same profile + same start date gives the same plan (deterministic, testable, explainable).

---

## 6. Adaptation (the plan follows reality)

| Event | What happens |
|---|---|
| Task done | topic progress updates; the last learning session schedules its spaced reviews |
| Task skipped | it's dropped; if it was a learning task, the topic moves into the next re-plan |
| Day missed | unfinished tasks roll to the next day with free time; if the backlog exceeds one day's capacity, the next 14 days are re-planned |
| Task moved | you pick a date; the scheduler checks that day's capacity |
| Weekly check-in (3 questions: hours you really had, how hard it felt, anything coming up) | completion rate updates capacity (§5.1); busy dates are added; too hard/easy adjusts problem difficulty |
| New interview result | topic average < 60 → re-learn + review tasks for that topic; ≥ 75 → its checkpoint counts as passed |
| New resume / JD gaps | matching topics get higher priority; skills with no topic (e.g. "Docker") become a project milestone or a "learn X basics" task |
| Profile edited | full re-plan from today; completed topics stay completed |

When a checkpoint is passed, the matching `skill_gaps` rows get `resolved_at`, which closes the loop with the
resume and interview pillars.

---

## 7. Where the LLM is used (and checked)

| Use | Input | Output (Pydantic) | Checks |
|---|---|---|---|
| **Roadmap summary** (`planner_summary.v1`) | profile, allocation, phases, feasibility (all from code) | 3-5 sentence overview + one paragraph per phase | may only mention topics/subjects that are in the plan; **no numbers from the LLM** (hours and dates are inserted by code into placeholders); falls back to a template |
| **Project ideas** (`planner_projects.v1`) | role, level, preferred stack, resume projects (redacted profile), open gaps | 2-3 ideas, each: title, why it fits, tech, 4-6 milestones | tech must come from your stack, your gaps or the role add-on list; ideas must not duplicate resume projects; milestones become project tasks with code-assigned sizes |

Both run in a background task after the plan is created; the roadmap shows immediately and the text fills in a
few seconds later. Same `LLMClient` as the other pillars (schema validation, repair retry, fallback, logging).

---

## 8. Data model (migration `20261127000000_planner_v2.sql`)

```sql
create table public.planner_profiles (            -- one per user: the questionnaire answers
  user_id    uuid primary key references auth.users(id) on delete cascade,
  answers    jsonb not null,                       -- validated PlannerProfile
  updated_at timestamptz not null default now()
);

create table public.plans (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null references auth.users(id) on delete cascade,
  status             text not null default 'active' check (status in ('active', 'archived')),
  start_date         date not null,
  target_date        date not null,
  profile_snapshot   jsonb not null,               -- answers used for this plan
  allocation         jsonb not null,               -- minutes per subject, planned vs capacity
  phases             jsonb not null,               -- phases with date ranges and weekly milestones
  feasibility        jsonb not null,               -- fits, cut topics, suggestion
  capacity_factor    numeric not null default 0.85,
  summary            jsonb,                        -- LLM text (or template)
  projects           jsonb,                        -- LLM project ideas
  curriculum_version text not null,
  created_at         timestamptz not null default now()
);

create table public.plan_topics (                  -- progress per topic
  id           uuid primary key default gen_random_uuid(),
  plan_id      uuid not null references public.plans(id) on delete cascade,
  user_id      uuid not null references auth.users(id) on delete cascade,
  topic_id     text not null,
  subject      text not null,
  priority     text not null,
  source       text not null default 'curriculum' check (source in ('curriculum', 'resume_gap', 'jd_gap', 'interview_gap')),
  planned_minutes int not null,
  done_minutes    int not null default 0,
  status       text not null default 'planned' check (status in ('planned', 'in_progress', 'done', 'cut')),
  learned_on   date,
  review_stage int not null default 0,               -- 0..3 (+2, +7, +21 days)
  created_at   timestamptz not null default now(),
  unique (plan_id, topic_id)
);

create table public.plan_tasks (
  id         uuid primary key default gen_random_uuid(),
  plan_id    uuid not null references public.plans(id) on delete cascade,
  user_id    uuid not null references auth.users(id) on delete cascade,
  date       date not null,
  position   int not null,
  kind       text not null check (kind in ('learn', 'practice', 'review', 'project', 'mock', 'checkpoint', 'catch_up')),
  subject    text not null,
  topic_id   text,
  title      text not null,
  minutes    int not null,
  details    jsonb not null default '{}',            -- problems, resource, interview link, session k/n
  status     text not null default 'todo' check (status in ('todo', 'done', 'skipped')),
  done_at    timestamptz,
  created_at timestamptz not null default now()
);

create table public.plan_checkins (
  id              uuid primary key default gen_random_uuid(),
  plan_id         uuid not null references public.plans(id) on delete cascade,
  user_id         uuid not null references auth.users(id) on delete cascade,
  week_start      date not null,
  planned_minutes int not null,
  done_minutes    int not null,
  difficulty      text check (difficulty in ('too_easy', 'right', 'too_hard')),
  note            text,
  created_at      timestamptz not null default now(),
  unique (plan_id, week_start)
);
-- indexes on (user_id, date) for plan_tasks; RLS owner-only on every table (same shape as resume/interview).
```

---

## 9. API (`/api/v2`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/planner/profile` | saved answers, or pre-filled suggestions from resume / interviews / gaps |
| PUT | `/planner/profile` | save answers (validated `PlannerProfile`) |
| POST | `/plans/preview` | run selection + feasibility + allocation **without saving**: the wizard's last step shows "fits / doesn't fit" |
| POST | `/plans` | create the plan (archives the previous one); text generation in the background |
| GET | `/plans/current` | roadmap: phases, milestones, allocation, feasibility, progress per subject |
| GET | `/plans/current/tasks?from=&to=` | tasks for a date range (today, this week) |
| PATCH | `/tasks/{id}` | `{status: done \| skipped \| todo}` |
| POST | `/tasks/{id}/move` | `{date}`; capacity checked |
| POST | `/plans/current/replan` | rebuild from today, keeping completed work |
| POST | `/plans/current/checkins` | weekly check-in |
| GET | `/planner/summary` | for dashboard / coach: today's tasks, week progress, streak, next milestone, behind or on track |

---

## 10. Frontend

- **`/dashboard/planner/setup`:** a 5-step wizard with conditional questions, pre-filled values marked "from your
  resume" or "from your interviews", and a final **preview**: weeks, hours/week, subject mix chart, fits or
  doesn't (with the suggestion), then "Create my plan".
- **`/dashboard/planner` (Today):** today's tasks with time boxes, checkboxes and "skip / move"; DSA tasks show
  the suggested problems; checkpoints have a "Start mock interview" button; a week strip shows progress.
- **Roadmap tab:** a phase timeline with weekly milestones, a subject mix (planned vs done), the feasibility note,
  the AI summary and project ideas.
- **Progress tab:** per-subject progress, topics done/reviewed, completion rate vs plan, streak.
- **Weekly check-in** card on Mondays (three questions).
- **Replaces** the legacy Task Planner page, `features/tasks/*`, the dashboard task cards' data source, the
  `AppContext` task state, and the legacy `system_ai` roadmap endpoints.

---

## 11. Step-by-step implementation

Every step ends with tests passing, lint/type checks clean, and a commit to `main`.

### P0 — Prep (0.5 d)
Migration + RLS, settings (buffer, review offsets, horizon days), `app/planner/` package skeleton.

### P1 — Curriculum (2 d)
YAML for DSA, OS, DBMS, CN, OOP, LLD, HLD, projects, aptitude, interview practice, role add-ons; `weights.yaml`;
loader + validation (unique ids, prerequisites exist, no cycles). **Review checkpoint: you check topics, hour
estimates, suggested problems and resources.**

### P2 — Profile (1 d)
`PlannerProfile` schema with conditional validation (year required for students, experience for professionals),
profile API, pre-fill from resume profile, `skill_gaps` and interview summary.

### P3 — Selection, demand, capacity, feasibility (1.5 d)
Pure functions for §4 and §5.1-5.2, with table-driven tests per persona.

### P4 — Scheduler (3 d)
Phases, topological order, weekly mix, daily packing, task splitting, spaced reviews, checkpoints, catch-up
block, rolling 14-day horizon. **Property tests** for §5.5 over many generated profiles.

### P5 — Plans and tasks API (1.5 d)
Create / preview / current / tasks / patch / move; ownership tests; archive previous plan.

### P6 — Adaptation (1.5 d)
Rollover, re-plan, weekly check-in + capacity factor, interview-result and gap ingestion, resolving `skill_gaps`.

### P7 — LLM text (1 d)
`planner_summary.v1` and `planner_projects.v1` prompts, fake handlers, validation (topics in plan, no numbers,
tech allow-list), template fallbacks, background generation.

### P8 — Frontend: wizard + preview (2 d)
Regenerate API types, hooks, the five-step wizard with conditional questions and pre-fill, preview screen.

### P9 — Frontend: today, roadmap, progress, check-in (2.5 d)
Task list with done/skip/move, roadmap timeline, subject chart, progress, check-in card.

### P10 — Evals, E2E, switchover, guide (1.5 d)
- **Persona eval** (`evals/planner/personas.yaml`), about 8 profiles:
  - your own profile (3rd-year B.Tech, backend/AI, product companies, Python)
  - a 1st-year with 1 h/day
  - a 4th-year targeting service companies
  - a BCA graduate
  - a 2-year backend engineer (1 h weekdays + 5 h weekends) targeting SDE-2
  - a 4-year engineer targeting senior roles
  - an overloaded profile that doesn't fit
  - a profile with a rest day and exam weeks
- For each persona the report shows subject shares, weeks, feasibility, first-week tasks, and the §5.5 checks.
  It runs in CI (no LLM needed).
- **E2E:** wizard → preview → plan → tick a task → re-plan.
- Delete the legacy planner code; write the study guide `docs/learn/task-planner-guide.md`.

**Total: about 18 days.**

---

## 12. How other pillars use this

| Pillar | Reads / writes |
|---|---|
| Resume screener | gaps → topic priorities; planner resolves gaps when topics are done |
| Interviews | topic averages → re-learn tasks; checkpoints open the interview setup with a topic preselected |
| Dashboard | `GET /planner/summary`: today's tasks, on track / behind, streak, next milestone |
| Coach chat | tools: `get_today_tasks`, `mark_task_done`, `move_task`, `replan`, `explain_plan` |

---

## 13. Later / optional
- **Free-text notes → plan changes:** "I'm weak at DP, mid-sems 10-20 March". The LLM maps the text to known
  topic ids and dates and shows them for confirmation (validated against the curriculum).
- **Diagnostic quiz** instead of self-rating: a 10-minute fundamentals mock that sets ratings from evidence.
- **Reminders:** email/push at your usual study time; calendar (.ics) export.
- **Problem tracking:** link LeetCode/GFG usernames to count solved problems automatically.
- **Company packs:** company-specific topic weights (written by you from interview experiences).
- **More roles:** DevOps, mobile, QA tracks.

---

## 14. Decisions needed from you before P0

1. **Aptitude subject** only when "service-based" is chosen (recommended), or never?
2. **Role add-on** topics at ~5% of time (recommended), or core subjects only for now?
3. **Rolling 14-day detail** plus weekly milestones for the rest (recommended), or every day of the full roadmap
   generated up front?
4. **Free-text notes** later (recommended), or in the MVP?
5. **Curriculum content:** OK for me to draft topics, hour estimates, suggested problems and free resources for
   you to review at P1?
6. **Default buffer** 15%, re-measured from your check-ins (recommended)?

---

## 15. CV impact (honest, only after P10)

Drafts; numbers come from the persona eval and tests:
- "Built a personalised study planner that turns a 5-step profile (level, role, company type, college year,
  weekday/weekend hours) into a dated roadmap across DSA, CS fundamentals, LLD/HLD and projects, using a
  deterministic constraint scheduler with spaced reviews; property-tested to never exceed daily capacity or break
  topic prerequisites."
- "Designed an LLM-Modulo pipeline: code owns dates, hours and ordering; the LLM writes roadmap explanations and
  project ideas validated against the plan; the plan re-adapts from completion rates and interview results."
- "Closed the loop across modules: resume, JD and interview gaps feed planner priorities; passed interview
  checkpoints resolve the gaps."
