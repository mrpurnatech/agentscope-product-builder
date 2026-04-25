Run the project test suite.

Steps:
1. Activate venv: `source .venv/bin/activate`
2. Run `pytest tests/ -v --tb=short`
3. Report pass/fail counts and any failures with file:line references
4. If no tests exist yet, suggest which modules need test coverage most (prioritize `core/gateway.py`, `guardrails/guardrails_check.py`, and agents)
