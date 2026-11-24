You compare a candidate's resume bullets with a job's requirements. Be strict and evidence-based.
Personal details were removed on purpose. The role is: $jd_title

1. `judgments`: for EACH requirement below, decide:
   - "strong"  = a bullet clearly shows the candidate did this
   - "partial" = related experience, but weaker or only part of the requirement
   - "missing" = nothing in the bullets shows it
   `evidence_bullet_ids` must be IDs from the bullet list (empty if missing). Never cite a bullet that
   doesn't actually support the requirement. Being listed in a skills section is NOT evidence.
2. `role_alignment` (0-5): how well the candidate's overall direction fits this role.
3. `tailored_bullets`: up to 5 bullets whose wording could better match the JD vocabulary.
   Rewrite each (max 30 words) using the JD's terms ONLY for things the bullet already says.
   NEVER add numbers, technologies, companies or claims that are not in the original bullet.
   Use [X] where a metric would help.
4. `summary_suggestion`: a 1-2 line professional summary for this application, built only from
   facts in the bullets and skills below. No numbers that aren't in them.

Requirements (JSON):
"""
$requirements_json
"""

Candidate bullets (JSON):
$bullets_json

Candidate skills section: $skills
