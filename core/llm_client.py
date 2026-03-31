import anthropic
from config.settings import ANTHROPIC_API_KEY

# Single shared client — all agents use this
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def ask(
    prompt: str,
    model: str,
    system: str = None,
    max_tokens: int = 1024
) -> str:
    """
    Central function all agents use to call Claude.
    Handles response parsing and cleanup.
    """
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)
    return response.content[0].text.strip()


def parse_json(text: str) -> dict:
    """
    Safely parse JSON from Claude response.
    Handles markdown code fences automatically.
    """
    import json
    raw = text.strip()
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else parts[0]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())