import json
from core.llm_client import ask
from config.settings import DEFAULT_MODEL, MAX_TOKENS_CODE


def run(requirement: str, plan: dict, file_info: dict) -> str:
    print(f"  [CoderAgent] Writing {file_info['path']}...")

    system = f"""You are a senior {plan['stack']} developer.
Write production-ready fully functional code.
Rules:
- Complete implementation no stubs or TODOs
- Full error handling with proper HTTP status codes
- Input validation on all endpoints
- Security best practices no hardcoded secrets
- Logging throughout
- Type hints for Python or JSDoc for Node.js
- Follow {plan['framework']} best practices
Return ONLY raw file content no markdown no explanation."""

    prompt = f"""Project: {requirement}
Stack: {plan['stack']} / {plan['framework']}
Dependencies: {', '.join(plan['dependencies'])}
Environment variables: {', '.join(plan.get('environment_vars', []))}
All project files: {json.dumps([f['path'] for f in plan['files']])}

Write complete production code for:
Path: {file_info['path']}
Purpose: {file_info['purpose']}"""

    return ask(
        prompt=prompt,
        model=DEFAULT_MODEL,
        system=system,
        max_tokens=MAX_TOKENS_CODE
    )