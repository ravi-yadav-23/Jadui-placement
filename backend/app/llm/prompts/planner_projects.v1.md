Suggest portfolio projects for a student preparing for software engineering placements.

Candidate (JSON):
"""
$candidate_json
"""

Suggest up to $count projects that would make this candidate stronger for the target role. For each:
- `title`: a short, concrete name (not a buzzword).
- `why`: one sentence on why it fits the target role and what an interviewer could ask about it.
- `tech`: 3-6 technologies, chosen ONLY from `allowed_tech`.
- `milestones`: 4-6 short actions in build order (e.g. "Model the booking tables and write the API").

Rules:
- Do not repeat or rename a project already in `existing_projects`.
- Prefer projects that use the candidate's `gaps` where they fit, so the project closes those gaps.
- Realistic for one person in 6-8 weeks of evenings and weekends. No claims about users or revenue.
