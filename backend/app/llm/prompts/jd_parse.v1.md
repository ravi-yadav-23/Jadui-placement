You extract the requirements from a job description into JSON. Extract; never invent.

Rules:
1. `requirements`: every distinct qualification or skill requirement, written short and close to the JD wording.
   - kind = "must" if it is required (sections like "Requirements", "Qualifications", "You have", "Must have").
   - kind = "nice" if it is optional ("Nice to have", "Preferred", "Bonus", "Plus", "Good to have").
   - If the JD does not separate them, treat clearly required items as "must" and the rest as "nice".
   - `skills`: the technologies/skills named in that requirement (e.g. ["Python", "REST APIs"]).
2. `knockouts`: ONLY hard eligibility conditions: graduation year/batch, minimum CGPA/percentage,
   on-site location or relocation, notice period / joining date, work authorization / visa, a required degree.
   `value` must be copied exactly as written in the JD.
3. `seniority`: intern, entry (0-2 years / new grad), mid, senior, or unknown.
4. `keywords`: 10-15 terms a recruiter would type into a search for this role.
5. `responsibilities`: what the person will do, short phrases.

Job description:
"""
$jd_text
"""
