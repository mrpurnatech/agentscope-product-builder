import json
from core.gateway import gateway


def ask(
    prompt: str,
    model: str = None,
    system: str = None,
    max_tokens: int = 1024,
    task_type: str = "default"
) -> str:
    """
    Central function all agents use to call Claude.
    Routes through OpenClaw gateway automatically.
    """
    return gateway.call(
        prompt=prompt,
        task_type=task_type,
        system=system,
        max_tokens=max_tokens,
        model=model
    )


def parse_json(text: str) -> dict:
    """
    Safely parse JSON from Claude response.
    Handles markdown code fences automatically.
    """
    raw = text.strip()
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else parts[0]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())