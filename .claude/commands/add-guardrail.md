Add a new guardrail check to the security layer.

Arguments: $ARGUMENTS (guardrail type and description, e.g. "input: block SQL injection attempts")

Steps:
1. Parse whether this is an input or output guardrail from $ARGUMENTS
2. Open `guardrails/guardrails_check.py`
3. For input guardrails:
   - Add a new `check_*` function following existing pattern (returns `Tuple[bool, str]`)
   - Wire it into `guard_input()` checks list
4. For output guardrails:
   - Add pattern to `SECRET_PATTERNS` or create new pattern list
   - Wire it into `guard_output()` or `scan_code_for_secrets()`
5. Update `guardrails/config/config.yml` to declare the new flow
6. Add a test in `tests/` for the new guardrail
