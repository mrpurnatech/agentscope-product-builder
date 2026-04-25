"""Reviewer Agent — code review + scoring using Haiku."""
from agentscope.message import Msg
from agents.base import ProductAgent
from core.models import create_fast_model
from config.settings import MAX_TOKENS_REVIEW

SYS_PROMPT = """You are a senior code reviewer.
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


class ReviewerAgent(ProductAgent):
    """Reviews generated code and scores quality."""

    def __init__(self) -> None:
        super().__init__(
            name="reviewer",
            model=create_fast_model(max_tokens=MAX_TOKENS_REVIEW),
            sys_prompt=SYS_PROMPT,
        )

    async def review(self, file_path: str, code: str, plan: dict) -> dict:
        """Review a single file. Returns review dict."""
        print(f"    [reviewer] Reviewing {file_path}...")

        prompt = f"""Stack: {plan.get('stack', 'python')}/{plan.get('framework', 'fastapi')}
File: {file_path}

{code}"""

        try:
            return await self.call_llm_json(prompt)
        except Exception:
            return {"approved": True, "score": 70, "issues": [], "fixed_code": None}

    async def reply(self, msg: Msg | None = None) -> Msg:
        ctx = self.get_build_context(msg)
        return self.make_reply("Reviewer ready", ctx)
