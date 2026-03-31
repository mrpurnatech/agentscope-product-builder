from core.llm_client import ask, parse_json
from config.settings import DEFAULT_MODEL, MAX_TOKENS_PLAN

SYSTEM = """You are a senior software architect.
Analyze the product requirement and create a complete project plan.
Respond ONLY with raw JSON:
{
  "repo_name": "kebab-case-name",
  "description": "one sentence description",
  "stack": "python or nodejs",
  "framework": "fastapi or flask or express",
  "private": false,
  "features": ["feature1", "feature2"],
  "files": [
    {"path": "file/path.ext", "purpose": "what this file does"}
  ],
  "dependencies": ["dep1", "dep2"],
  "environment_vars": ["VAR_NAME=description"]
}
Always include: main app, models, routes, services, config,
tests, Dockerfile, CI workflow, README, .env.example."""


def run(requirement: str) -> dict:
    print(f"\n[PlannerAgent] Planning: {requirement[:60]}...")
    raw = ask(
        prompt=f"Product requirement: {requirement}",
        model=DEFAULT_MODEL,
        system=SYSTEM,
        max_tokens=MAX_TOKENS_PLAN
    )
    plan = parse_json(raw)
    print(f"  Stack:    {plan['stack']}/{plan['framework']}")
    print(f"  Features: {len(plan['features'])}")
    print(f"  Files:    {len(plan['files'])}")
    return plan