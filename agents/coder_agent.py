"""Coder Agent — production code generation using Sonnet."""
import json
from agentscope.message import Msg
from agents.base import ProductAgent
from core.models import create_default_model
from config.settings import MAX_TOKENS_CODE


class CoderAgent(ProductAgent):
    """Writes production-ready code for a single file."""

    def __init__(self) -> None:
        super().__init__(
            name="coder",
            model=create_default_model(max_tokens=MAX_TOKENS_CODE),
            sys_prompt="",  # Set dynamically per call
        )

    async def generate(
        self,
        service_context: str,
        plan: dict,
        file_info: dict,
    ) -> str:
        """Generate code for a single file. Returns raw code string."""
        stack = plan.get("stack", "python")
        framework = plan.get("framework", "fastapi")

        print(f"    [coder] Writing {file_info['path']}...")

        self.sys_prompt = f"""You are a senior {stack} developer building production systems.
Write production-ready, fully functional code.

Rules:
- Complete implementation — NO stubs, NO TODOs, NO placeholders
- Full error handling with proper HTTP status codes
- Input validation on all endpoints
- Security best practices — no hardcoded secrets, use env vars
- Logging throughout with structured log format
- Type hints for Python, TypeScript types for Node.js
- Follow {framework} best practices and conventions
- Proper imports — use relative imports within the service
- Handle edge cases (empty inputs, not found, duplicates)
- Use async/await where appropriate

Return ONLY raw file content. No markdown fences. No explanation."""

        prompt = f"""Context:
{service_context}

Service Plan:
- Stack: {stack} / {framework}
- Dependencies: {', '.join(plan.get('dependencies', plan.get('packages', [])))}
- Environment variables: {', '.join(plan.get('environment_vars', []))}
- All project files: {json.dumps([f['path'] for f in plan.get('files', [])])}

Write complete production code for:
Path: {file_info['path']}
Purpose: {file_info['purpose']}"""

        return await self.call_llm(prompt)

    async def reply(self, msg: Msg | None = None) -> Msg:
        ctx = self.get_build_context(msg)
        return self.make_reply("Coder ready", ctx)
