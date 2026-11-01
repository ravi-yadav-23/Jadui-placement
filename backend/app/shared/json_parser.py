import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

def extract_json_from_llm_response(raw: str) -> dict[str, Any]:
    """
    Extracts and parses JSON from a potentially messy LLM response.
    Handles markdown code fences (```json ... ```) and standard parsing errors.
    """
    if not raw or not raw.strip():
        return {}

    text = raw.strip()

    # Try extracting from code fences
    if "```json" in text:
        try:
            extracted = text.split("```json")[1].split("```")[0].strip()
            return json.loads(extracted)
        except Exception as e:
            logger.warning(f"Failed to parse JSON inside markdown block: {e}")

    # Fallback to general code block if ```json isn't matched
    if "```" in text:
        try:
            extracted = text.split("```")[1].strip()
            # If the block started with ``` but no json tag, there might be a trailing newline
            return json.loads(extracted)
        except Exception:
            pass

    # Try raw parse
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"Direct JSON parse failed: {e}. Raw text snippet: {text[:100]}")
        return {}
