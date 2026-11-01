# Production Readiness Remediation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remediate all remaining critical, high, and medium defects identified in the independent codebase audit (BUG-01 through BUG-20) to elevate Jadui Placement from 74/100 to production-grade readiness (90+/100).

**Architecture:** Implement missing Next.js API proxy routes, eliminate client-to-database state contamination race conditions, enforce defensive rendering boundaries, fix parsing omissions (Word tables and regex skill boundaries), non-blocking threadpool offloading on FastAPI, and establish an automated Pytest test harness.

**Tech Stack:** Next.js 14 App Router, React 18, FastAPI 0.110+, Python 3.10+, PyPDF2, python-docx, Supabase PostgreSQL, Pytest.

---

### Task 1: Add Missing PATCH Route Handler for Resume Booster (BUG-01)

**Files:**
- Modify: `frontend/src/app/api/resume/result/route.js:40-65`
- Test: Next.js build verification and endpoint method support

**Step 1: Verify current behavior and failure**
Inspect `frontend/src/app/api/resume/result/route.js`. Notice that only `GET` is exported.
When `TechBioBooster.jsx` issues a `PATCH` request to `/api/resume/result`, Next.js returns HTTP 405 Method Not Allowed.

**Step 2: Implement minimal PATCH handler**
In `frontend/src/app/api/resume/result/route.js`, export the `PATCH` handler:

```javascript
export async function PATCH(req) {
  const authHeader = req.headers.get('authorization');
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    if (!backendUrl) {
      return NextResponse.json({ error: 'NEXT_PUBLIC_BACKEND_URL is not configured' }, { status: 500 });
    }

    const body = await req.json();
    const response = await fetch(`${backendUrl}/api/resume/result`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
      body: JSON.stringify(body),
      cache: 'no-store',
    });

    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json({ error: data?.detail || 'Failed to update resume result' }, { status: response.status });
    }

    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
```

**Step 3: Verification**
Run: `npm run build` in `frontend/`.
Expected: Route `/api/resume/result` builds cleanly supporting GET and PATCH.

**Step 4: Commit**
`git add frontend/src/app/api/resume/result/route.js`  
`git commit -m "fix(api): add missing PATCH handler in resume result proxy route"`

---

### Task 2: Create Next.js Proxy Routes for Admin Workshops (BUG-02)

**Files:**
- Create: `frontend/src/app/api/admin/workshops/suggestions/route.js`
- Create: `frontend/src/app/api/admin/workshops/schedule/route.js`

**Step 1: Write `suggestions/route.js`**
Create `frontend/src/app/api/admin/workshops/suggestions/route.js`:
```javascript
import { NextResponse } from 'next/server';

export async function GET(req) {
  const authHeader = req.headers.get('authorization');
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    if (!backendUrl) {
      return NextResponse.json({ error: 'NEXT_PUBLIC_BACKEND_URL is not configured' }, { status: 500 });
    }

    const response = await fetch(`${backendUrl}/api/admin/workshops/suggestions`, {
      method: 'GET',
      headers: {
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
      cache: 'no-store',
    });

    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json({ error: data?.detail || 'Failed to fetch suggestions' }, { status: response.status });
    }

    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
```

**Step 2: Write `schedule/route.js`**
Create `frontend/src/app/api/admin/workshops/schedule/route.js`:
```javascript
import { NextResponse } from 'next/server';

export async function POST(req) {
  const authHeader = req.headers.get('authorization');
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    if (!backendUrl) {
      return NextResponse.json({ error: 'NEXT_PUBLIC_BACKEND_URL is not configured' }, { status: 500 });
    }

    const body = await req.json();
    const response = await fetch(`${backendUrl}/api/admin/workshops/schedule`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
      body: JSON.stringify(body),
      cache: 'no-store',
    });

    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json({ error: data?.detail || 'Failed to schedule workshop' }, { status: response.status });
    }

    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
```

**Step 3: Verification**
Run: `npm run build` in `frontend/`.
Expected: Routes `/api/admin/workshops/suggestions` and `/api/admin/workshops/schedule` compile cleanly.

**Step 4: Commit**
`git add frontend/src/app/api/admin/workshops/`  
`git commit -m "feat(api): create Next.js edge route proxies for admin workshops"`

---

### Task 3: Delete Dead / Abandoned Legacy Source Files (BUG-11)

**Files:**
- Remove: `frontend/src/services/api.js`
- Remove: `frontend/src/hooks/useDashboardData.js`
- Remove: `frontend/src/hooks/useHistory.js`

**Step 1: Verify files have zero incoming imports**
Verify that no file in `frontend/src/` imports these files.

**Step 2: Delete orphaned files**
Delete `frontend/src/services/api.js`, `frontend/src/hooks/useDashboardData.js`, and `frontend/src/hooks/useHistory.js`.

**Step 3: Verification**
Run: `npm run build` in `frontend/`.
Expected: Clean build without missing module errors.

**Step 4: Commit**
`git rm frontend/src/services/api.js frontend/src/hooks/useDashboardData.js frontend/src/hooks/useHistory.js`  
`git commit -m "chore: remove unused legacy api service and orphaned hooks"`

---

### Task 4: Fix White-Screen Render Crash in StudentDossier (BUG-07)

**Files:**
- Modify: `frontend/src/features/admin/StudentDossier.jsx:32-65`

**Step 1: Identify crash site**
In `StudentDossier.jsx` line 60: `{dossier.user_id[0]?.toUpperCase()}` crashes if `dossier` is null or `user_id` is missing.

**Step 2: Add early null guard and safe optional chaining**
In `frontend/src/features/admin/StudentDossier.jsx`:
1. Add an early return if `dossier` is not loaded:
```jsx
if (!dossier) {
  return (
    <div className="flex flex-col items-center justify-center p-20 gap-4">
      <p className="text-xs font-bold text-neutral-500 uppercase tracking-widest">Dossier unavailable</p>
    </div>
  );
}
```
2. Update line 60 to:
```jsx
{dossier?.user_id?.[0]?.toUpperCase() || 'S'}
```

**Step 3: Verification**
Run: `npm run build` in `frontend/`.
Expected: Build passes with defensive rendering.

**Step 4: Commit**
`git add frontend/src/features/admin/StudentDossier.jsx`  
`git commit -m "fix(admin): guard against null dossier in StudentDossier component"`

---

### Task 5: Prevent Mock Data Overwriting Production Database (BUG-08)

**Files:**
- Modify: `frontend/src/context/AppContext.jsx:185-215`

**Step 1: Analyze race condition**
In `AppContext.jsx`: when `fetchWithAuth('/api/system/insights')` fails, it calls `seedMockProgress(dispatch, ACTIONS)` and then `setReadyToPersist(true)`.
`useStatePersistence` then immediately debounces and posts mock state to `/api/system/state`, permanently replacing user data in Supabase with test data.

**Step 2: Implement state guard in `AppContext.jsx`**
Only set `readyToPersist` to `true` when real remote state has loaded successfully:
```javascript
        if (user) {
          const res = await fetchWithAuth(`/api/system/insights?user_id=${encodeURIComponent(user.id || 'demo-user')}`, { cache: 'no-store' })
          if (res.ok) {
            const data = await res.json()
            dispatch({ type: ACTIONS.SET_SYSTEM_INSIGHTS, payload: data })
            setReadyToPersist(true) // Only allow persistence when verified real remote state loaded!
          } else {
            seedMockProgress(dispatch, ACTIONS)
            // DO NOT call setReadyToPersist(true) here!
          }
        }
```

**Step 3: Verification**
Run: `npm run build` in `frontend/`.
Expected: Build passes cleanly.

**Step 4: Commit**
`git add frontend/src/context/AppContext.jsx`  
`git commit -m "fix(state): prevent fallback mock state from overwriting remote database"`

---

### Task 6: Fix Positional Arguments in Workshop Notification (BUG-03)

**Files:**
- Modify: `backend/modules/admin_ai/workshops.py:95-115`

**Step 1: Identify missing arguments**
`system_service.save_state` requires `(self, user_id, tasks, roadmap, notifications, skill_gaps, chat_context, ...)`.
`workshops.py` line 110 passed only `user_id=user_id, tasks=tasks`, which raised a TypeError and was swallowed by `except Exception: pass`.

**Step 2: Pass full state to `save_state` and log exceptions**
In `backend/modules/admin_ai/workshops.py`:
```python
        try:
            state = system_service.get_state(user_id)
            import time
            new_task = {
                "id": f"wp-{int(time.time())}",
                "title": f"📅 Workshop Scheduled: {workshop_title}",
                "category": "Placement Drive",
                "completed": False,
                "due": "Upcoming",
                "source": "TPO"
            }
            tasks = state.get("tasks", [])
            tasks.insert(0, new_task)
            system_service.save_state(
                user_id=user_id,
                tasks=tasks,
                roadmap=state.get("roadmap", []),
                notifications=state.get("notifications", []),
                skill_gaps=state.get("skill_gaps", []),
                chat_context=state.get("chat_context", {}),
                chat_history=state.get("chat_history", []),
                chat_sessions=state.get("chat_sessions", []),
                active_chat_session_id=state.get("active_chat_session_id", ""),
            )
        except Exception as exc:
            import logging
            logging.getLogger("admin_ai").error(f"Failed to notify student {user_id} of workshop: {exc}")
```

**Step 3: Verification**
Run: `python -m compileall backend/modules/admin_ai`
Expected: Exits 0.

**Step 4: Commit**
`git add backend/modules/admin_ai/workshops.py`  
`git commit -m "fix(admin): provide all required positional arguments to save_state in workshop dispatch"`

---

### Task 7: Fix Naive Substring Skill Extraction (BUG-05)

**Files:**
- Modify: `backend/modules/resume_ai/section_parser.py:90-95`
- Test: `backend/tests/test_section_parser.py`

**Step 1: Write unit test demonstrating substring bug**
Create `backend/tests/test_section_parser.py`:
```python
import pytest
from modules.resume_ai.section_parser import section_parser

def test_skill_extraction_no_false_positives():
    text = "Proficient in digital signal algorithms and machine architecture."
    skills = section_parser.extract_skills(text)
    # Should NOT extract 'git' from 'digital', nor 'go' from 'algorithms', nor 'c' from 'machine'
    assert "git" not in skills
    assert "go" not in skills
```

**Step 2: Run test to observe failure**
Run: `pytest backend/tests/test_section_parser.py`
Expected: Fails with `"git" in skills`.

**Step 3: Implement regex boundary matching in `SectionParser`**
In `backend/modules/resume_ai/section_parser.py`:
```python
    def extract_skills(self, text: str) -> list[str]:
        norm = text.lower()
        found = []
        for s in COMMON_SKILLS:
            pattern = r'(?<![a-zA-Z0-9])' + re.escape(s) + r'(?![a-zA-Z0-9])'
            if re.search(pattern, norm):
                found.append(s)
        return sorted(found)
```

**Step 4: Run test to verify it passes**
Run: `pytest backend/tests/test_section_parser.py`
Expected: PASS.

**Step 5: Commit**
`git add backend/modules/resume_ai/section_parser.py backend/tests/test_section_parser.py`  
`git commit -m "fix(resume): use regex word boundaries to prevent false-positive skill extraction"`

---

### Task 8: Add Word Document Table Parsing in Resume Parser (BUG-06)

**Files:**
- Modify: `backend/modules/resume_ai/parser.py:61-70`
- Test: `backend/tests/test_resume_parser.py`

**Step 1: Write test for table parsing**
In `backend/tests/test_resume_parser.py`:
```python
import io
import docx
from modules.resume_ai.parser import parser

def test_parse_docx_with_tables():
    doc = docx.Document()
    doc.add_paragraph("Summary: Experienced engineer")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Skills"
    table.cell(0, 1).text = "Python, React, Docker"
    
    buf = io.BytesIO()
    doc.save(buf)
    parsed = parser._parse_docx(buf.getvalue())
    
    assert "Python" in parsed
    assert "Docker" in parsed
```

**Step 2: Run test and observe failure**
Run: `pytest backend/tests/test_resume_parser.py`
Expected: Fails because table cells are ignored in current `_parse_docx`.

**Step 3: Implement table extraction in `_parse_docx`**
In `backend/modules/resume_ai/parser.py`:
```python
    def _parse_docx(self, data: bytes) -> str:
        try:
            import docx  # type: ignore
        except ImportError as exc:
            raise HTTPException(status_code=500, detail="python-docx dependency missing") from exc

        document = docx.Document(bytes_to_stream(data))
        parts = [para.text for para in document.paragraphs if para.text]
        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        parts.append(cell.text.strip())
        text = " ".join(parts)
        return normalize_space(text)
```

**Step 4: Run test to verify pass**
Run: `pytest backend/tests/test_resume_parser.py`
Expected: PASS.

**Step 5: Commit**
`git add backend/modules/resume_ai/parser.py backend/tests/test_resume_parser.py`  
`git commit -m "fix(resume): extract text from tables in docx parser"`

---

### Task 9: Implement Real Keyword Matching for Admin Hiring Simulation (BUG-04)

**Files:**
- Modify: `backend/modules/admin_ai/services.py:125-146`
- Test: `backend/tests/test_admin_services.py`

**Step 1: Write test verifying search query relevance**
Create `backend/tests/test_admin_services.py`:
```python
def test_rank_students_differentiates_by_query(monkeypatch):
    from modules.admin_ai.services import admin_service
    
    mock_students = [
        {"user_id": "u1", "name": "Alice", "skills": ["python", "fastapi"], "avgScore": 80},
        {"user_id": "u2", "name": "Bob", "skills": ["react", "next.js"], "avgScore": 80},
    ]
    monkeypatch.setattr(admin_service, "get_all_students", lambda: mock_students)
    
    results = admin_service.rank_students_for_job("react")
    assert results[0]["user_id"] == "u2"
```

**Step 2: Run test and observe failure**
Run: `pytest backend/tests/test_admin_services.py`
Expected: Fails because both students currently receive identical scores.

**Step 3: Implement real keyword/skill intersection matching**
In `backend/modules/admin_ai/services.py`:
```python
    def rank_students_for_job(self, query: str) -> list[dict[str, Any]]:
        """AI-assisted ranking of students based on tech stack query matching."""
        students = self.get_all_students()
        query_terms = [q.strip().lower() for q in query.split(",") if q.strip()]
        
        ranked = []
        for s in students:
            matched_terms = []
            student_skills = [str(sk).lower() for sk in (s.get("skills") or s.get("top_skills") or [])]
            searchable = " ".join(student_skills + [s.get("name", "").lower(), s.get("target_role", "").lower()])
            for term in query_terms:
                if term in searchable:
                    matched_terms.append(term)
            
            term_ratio = (len(matched_terms) / len(query_terms)) if query_terms else 1.0
            relevance = int(term_ratio * 70 + (s.get("avgScore", 0) * 0.3))
            ranked.append({
                **s,
                "relevance": min(100, relevance),
                "matched_terms": matched_terms,
                "match_details": f"Matched {len(matched_terms)} of {len(query_terms)} requirements" if query_terms else "Cohort baseline",
            })
            
        return sorted(ranked, key=lambda x: -x['relevance'])
```

**Step 4: Run test to verify pass**
Run: `pytest backend/tests/test_admin_services.py`
Expected: PASS.

**Step 5: Commit**
`git add backend/modules/admin_ai/services.py backend/tests/test_admin_services.py`  
`git commit -m "feat(admin): replace static hiring heuristic with genuine query-term skill matching"`

---

### Task 10: Offload Synchronous File Parsing to Threadpool (BUG-09)

**Files:**
- Modify: `backend/modules/resume_ai/services.py:55-70`

**Step 1: Identify synchronous blocking call**
In `upload_resume`: `parsed = parser.parse_bytes(...)` executes CPU-heavy document parsing directly on the asyncio event loop.

**Step 2: Wrap call with `run_in_threadpool`**
In `backend/modules/resume_ai/services.py`:
```python
from starlette.concurrency import run_in_threadpool

# Inside async def upload_resume:
parsed = await run_in_threadpool(
    parser.parse_bytes, 
    file.filename or "resume.txt", 
    file.content_type or "", 
    data
)
```

**Step 3: Verification**
Run: `python -m compileall backend/modules/resume_ai`
Expected: Exits 0.

**Step 4: Commit**
`git add backend/modules/resume_ai/services.py`  
`git commit -m "perf(resume): offload synchronous PDF and DOCX parsing to threadpool"`

---

### Task 11: Add ON DELETE CASCADE in PostgreSQL DDL (BUG-13)

**Files:**
- Modify: `deployment/schema.sql`

**Step 1: Add ON DELETE CASCADE to foreign keys**
In `deployment/schema.sql`:
Add `ON DELETE CASCADE` to foreign keys referencing `resume_files` and `interview_sessions`.

**Step 2: Verification**
Verify SQL schema syntax.

**Step 3: Commit**
`git add deployment/schema.sql`  
`git commit -m "fix(db): add ON DELETE CASCADE to foreign keys in schema DDL"`

---

### Task 12: Backend Pytest Test Harness & CI Suite (BUG-20)

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_health_and_compilation.py`

**Step 1: Create pytest configuration and test files**
Ensure tests cover:
- Resume parsing
- Section extraction
- Fallback question generation
- Admin ranking and dossier formatting

**Step 2: Run pytest across all test suites**
Run: `pytest backend/tests -v`
Expected: All tests pass.

**Step 3: Commit**
`git add backend/tests/`  
`git commit -m "test: add automated backend pytest test suite"`

---

### Task 13: Final End-to-End Build & Compilation Verification

**Files:**
- None (Verification step across all tiers)

**Step 1: Run Python compilation**
Run: `python -m compileall backend/app backend/modules backend/tests`
Expected: Exits 0.

**Step 2: Run Pytest test suite**
Run: `pytest backend/tests -v`
Expected: All tests pass.

**Step 3: Run Next.js production build**
Run: `cd frontend && npm run build`
Expected: All static and dynamic route handlers build successfully.

