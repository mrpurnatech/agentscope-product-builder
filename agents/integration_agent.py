"""Integration Agent — service wiring, shared types, middleware using Sonnet."""
import json
from agentscope.message import Msg
from agents.base import ProductAgent
from core.models import create_default_model
from config.settings import MAX_TOKENS_CODE

SYS_PROMPT = """You are a senior integration architect.
Generate all files needed to wire services together.

Generate:
1. Shared types for inter-service communication
2. Service client libraries (typed HTTP clients for internal APIs)
3. Event/message schemas for async communication
4. Middleware: auth, logging, error handling (shared across services)
5. API Gateway routing configuration
6. Health check endpoints

Rules:
- Type-safe inter-service communication
- Centralized error handling patterns
- Request/response logging middleware
- Circuit breaker patterns for resilience
- Correlation IDs for distributed tracing
- Health check endpoints on every service

Respond ONLY with raw JSON:
{
  "files": [
    {"path": "shared/types/user.ts", "content": "complete file content"},
    {"path": "shared/middleware/auth.py", "content": "JWT auth middleware"}
  ]
}"""


class IntegrationAgent(ProductAgent):
    """Generates integration layer files — shared types, clients, middleware."""

    def __init__(self) -> None:
        super().__init__(
            name="integration",
            model=create_default_model(max_tokens=MAX_TOKENS_CODE),
            sys_prompt=SYS_PROMPT,
        )

    async def reply(self, msg: Msg | None = None) -> Msg:
        ctx = self.get_build_context(msg)
        architecture = ctx.get("architecture", {})
        api_contracts = ctx.get("api_contracts", {})

        print("\n" + "=" * 60)
        print("PHASE 7: SERVICE INTEGRATION")
        print("=" * 60)

        prompt = f"""Generate all integration and shared files for this architecture:

Architecture:
{json.dumps(architecture, indent=2)}

API Contracts:
{json.dumps(api_contracts, indent=2)}

Generate:
1. Shared types/interfaces
2. Service client libraries for inter-service HTTP calls
3. Auth middleware (JWT validation)
4. Error handling middleware
5. Logging middleware with correlation IDs
6. Health check endpoint implementation
7. API Gateway routing configuration"""

        result = await self.call_llm_json(prompt)
        files = result.get("files", [])

        print(f"\n  Generated {len(files)} integration files:")
        for f in files:
            print(f"    - {f['path']}")

        # Add files to build context
        all_files = ctx.get("all_files", {})
        for f in files:
            all_files[f["path"]] = f["content"]
        ctx["all_files"] = all_files

        return self.make_reply(f"Generated {len(files)} integration files", ctx)
