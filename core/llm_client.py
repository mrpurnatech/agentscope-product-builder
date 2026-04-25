"""
Backward-compatible LLM client.

DEPRECATED: New agents should extend ProductAgent and use call_llm() / call_llm_json().
This module exists only for backward compatibility with any code
that still imports `ask` or `parse_json`.
"""
import json


def parse_json(text: str) -> dict:
    """Parse JSON from LLM response, stripping markdown fences."""
    raw = text.strip()
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else parts[0]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())
