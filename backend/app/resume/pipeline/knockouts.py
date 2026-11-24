"""Knockout checks: hard eligibility rules (CGPA cutoff, graduation batch, location).

These matter more than any keyword score: in real hiring they are what filters people out
automatically. We compare the JD's rule with the profile and say ok / conflict / unknown.
"""

import re

from app.resume.schemas import KnockoutDraft, KnockoutResult, ResumeProfile

NUMBER = re.compile(r"\d+(?:\.\d+)?")
YEAR = re.compile(r"\b20\d{2}\b")


def _best_cgpa_out_of_10(profile: ResumeProfile) -> float | None:
    values = []
    for edu in profile.education:
        if edu.cgpa is None:
            continue
        scale = edu.cgpa_scale or (4.0 if edu.cgpa <= 4 else 10.0)
        values.append(edu.cgpa * 10 / scale)
    return max(values) if values else None


def _grad_years(profile: ResumeProfile) -> set[int]:
    years = {edu.grad_year for edu in profile.education if edu.grad_year}
    for edu in profile.education:  # fall back to the end date, e.g. "2022 - 2026"
        years |= {int(y) for y in YEAR.findall(edu.end or "")}
    return years


def check_cgpa(rule: KnockoutDraft, profile: ResumeProfile) -> KnockoutResult:
    numbers = [float(n) for n in NUMBER.findall(rule.value)]
    candidate = _best_cgpa_out_of_10(profile)
    if not numbers or candidate is None:
        return KnockoutResult(type="cgpa", jd_value=rule.value, status="unknown",
                              message="Your resume doesn't show a CGPA, so this cutoff can't be checked.")
    required = numbers[0]
    if "%" in rule.value or required > 10:   # percentage cutoff: rough CGPA -> % conversion
        required = required / 9.5
    status = "ok" if candidate + 1e-9 >= required else "conflict"
    message = (f"Your CGPA (~{candidate:.2f}/10) meets the cutoff." if status == "ok"
               else f"Your CGPA (~{candidate:.2f}/10) is below the required {rule.value}.")
    return KnockoutResult(type="cgpa", jd_value=rule.value, resume_value=f"{candidate:.2f}/10", status=status,
                          message=message)


def check_grad_year(rule: KnockoutDraft, profile: ResumeProfile) -> KnockoutResult:
    wanted = {int(y) for y in YEAR.findall(rule.value)}
    have = _grad_years(profile)
    if not wanted or not have:
        return KnockoutResult(type="grad_year", jd_value=rule.value, status="unknown",
                              message="Couldn't compare graduation years; make your graduation year explicit.")
    status = "ok" if wanted & have else "conflict"
    shown = ", ".join(str(y) for y in sorted(have))
    message = ("Your graduation year matches." if status == "ok"
               else f"The JD asks for {rule.value}; your resume shows {shown}.")
    return KnockoutResult(type="grad_year", jd_value=rule.value, resume_value=shown, status=status, message=message)


def check_location(rule: KnockoutDraft, profile: ResumeProfile) -> KnockoutResult:
    city = re.sub(r"\(.*?\)|on-?site|hybrid|remote", "", rule.value, flags=re.I).strip(" ,-:")
    if profile.location and city and city.lower() in profile.location.lower():
        return KnockoutResult(type="location", jd_value=rule.value, resume_value=profile.location, status="ok",
                              message="You're in the job's location.")
    return KnockoutResult(type="location", jd_value=rule.value, resume_value=profile.location, status="unknown",
                          message=f"Confirm you can work from {city or rule.value}; mention relocation if relevant.")


CHECKERS = {"cgpa": check_cgpa, "grad_year": check_grad_year, "location": check_location}


def check_knockouts(rules: list[KnockoutDraft], profile: ResumeProfile) -> list[KnockoutResult]:
    results = []
    for rule in rules:
        checker = CHECKERS.get(rule.type)
        if checker:
            results.append(checker(rule, profile))
        else:  # notice period, work authorization, degree: answered in the application form, not the resume
            results.append(KnockoutResult(type=rule.type, jd_value=rule.value, status="unknown",
                                          message="Check this yourself; it's usually asked in the application form."))
    return results
