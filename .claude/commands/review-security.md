Review the security posture of the project.

Steps:
1. Read `guardrails/guardrails_check.py` and audit:
   - Injection patterns — are there gaps?
   - Secret patterns — any common formats missing?
   - Off-topic keywords — false positive risk?
2. Read `core/gateway.py` — check for API key exposure, error message leakage
3. Read `agents/github_agent.py` — check token handling, repo creation safety
4. Read `telegram_bot.py` — check auth enforcement, input sanitization
5. Scan all `.py` files for hardcoded secrets or credentials
6. Report findings with severity (critical/high/medium/low) and suggested fixes
