You are planning a mock technical interview for a student preparing for software engineering
placements. Target role: $target_role. Personal details were removed on purpose.

Write exactly $count interview questions. $focus

Items to ask about (JSON; every item has an "id"):
"""
$items_json
"""

Extra context about the candidate (JSON, may be empty):
$context_json

Rules for every question:
- `source_ids`: the id(s) of the item(s) the question is about, copied exactly from the list above.
  Never invent an id. Use a different item for each question when there are enough items.
- Ask the way a real interviewer probes a project: what the candidate personally built, why they
  chose a design, what went wrong and how they fixed it, how it would scale, or what they would change.
  Mix these angles across the questions. One question each, 1-3 sentences, no trivia.
- Never state facts about the candidate's work that are not in the items (no invented numbers,
  features or results). Ask, don't tell.
- `key_points`: 3-5 points a strong answer would cover. Describe what a good answer should
  contain (for example "explains why PostgreSQL was chosen over a document store"), not facts
  about this candidate's project.
- `concept`: 2-4 words naming the skill being tested (for example "API design", "Caching").
