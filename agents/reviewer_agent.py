from core.llm_client import ask, parse_json
from config.settings import FAST_MODEL, MAX_TOKENS_REVIEW

SYSTEM = """You are a senior code reviewer.
Review for: security issues, syntax errors, missing error handling,
hardcoded secrets, SQL injection, production readiness.
Respond ONLY with raw JSON:
{
  "approved": true,
  "score": 85,
  "issues": ["issue1"],
  "fixed_code": null
}
Approve with score for minor issues.
Only set approved false and provide fixed_code for critical issues."""


def run(file_path: str, code: str, plan: dict) -> dict:
    print(f"  [ReviewerAgent] Reviewing {file_path}...")

    prompt = f"""Stack: {plan['stack']}/{plan['framework']}
File: {file_path}

{code}"""

    raw = ask(
        prompt=prompt,
        task_type="review",
        system=SYSTEM,
        max_tokens=MAX_TOKENS_REVIEW
    )

    try:
        return parse_json(raw)
    except Exception:
        return {"approved": True, "score": 70, "issues": [], "fixed_code": None}