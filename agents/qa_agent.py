from core.llm_client import ask
from config.settings import FAST_MODEL, MAX_TOKENS_QA

SKIP = [
    "test_", ".gitignore", "README", "Dockerfile",
    "requirements", "package.json", ".env", "workflow", ".gitkeep"
]


def run(requirement: str, plan: dict, file_path: str, code: str) -> str:
    if any(p in file_path for p in SKIP):
        return None

    print(f"  [QAAgent] Writing tests for {file_path}...")

    system = f"""You are a QA engineer writing tests for {plan['stack']}.
Write comprehensive tests covering:
- Happy path scenarios
- Edge cases and error conditions
- Input validation
Use pytest for Python or Jest for Node.js.
Return ONLY raw test file content."""

    prompt = f"""Project: {requirement}
File to test: {file_path}

Source code:
{code[:2000]}"""

    return ask(
        prompt=prompt,
        model=FAST_MODEL,
        system=system,
        max_tokens=MAX_TOKENS_QA
    )