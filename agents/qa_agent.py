"""QA Agent — test generation using Haiku."""
from agentscope.message import Msg
from agents.base import ProductAgent
from core.models import create_fast_model
from config.settings import MAX_TOKENS_QA

SKIP = [
    "test_", ".gitignore", "README", "Dockerfile",
    "requirements", "package.json", ".env", "workflow", ".gitkeep"
]


class QAAgent(ProductAgent):
    """Generates tests for source files."""

    def __init__(self) -> None:
        super().__init__(
            name="qa",
            model=create_fast_model(max_tokens=MAX_TOKENS_QA),
            sys_prompt="",  # Set dynamically
        )

    async def generate_tests(
        self,
        requirement: str,
        plan: dict,
        file_path: str,
        code: str,
    ) -> str | None:
        """Generate tests for a file. Returns test code or None."""
        if any(p in file_path for p in SKIP):
            return None

        print(f"    [qa] Writing tests for {file_path}...")

        stack = plan.get("stack", "python")
        self.sys_prompt = f"""You are a QA engineer writing tests for {stack}.
Write comprehensive tests covering:
- Happy path scenarios
- Edge cases and error conditions
- Input validation
Use pytest for Python or Jest for Node.js.
Return ONLY raw test file content."""

        prompt = f"""Project: {requirement}
File to test: {file_path}

Source code:
{code[:3000]}"""

        return await self.call_llm(prompt)

    async def reply(self, msg: Msg | None = None) -> Msg:
        ctx = self.get_build_context(msg)
        return self.make_reply("QA ready", ctx)
