"""DevOps Agent — Docker, CI/CD, infrastructure using Sonnet."""
import json
from agentscope.message import Msg
from agents.base import ProductAgent
from core.models import create_default_model
from config.settings import MAX_TOKENS_CODE

SYS_PROMPT = """You are a senior DevOps/Platform engineer.
Generate ALL infrastructure files for a multi-service architecture.

Generate:
1. Dockerfile per service (multi-stage builds, non-root user, health checks)
2. docker-compose.yml (all services, databases, message queues, networks)
3. docker-compose.override.yml (dev overrides: volumes, debug ports)
4. .dockerignore per service
5. GitHub Actions CI/CD workflow (.github/workflows/ci.yml)
6. Makefile with common commands
7. .env.example for the entire project
8. nginx.conf if API gateway needed

Rules:
- Multi-stage Docker builds for minimal image size
- Non-root users in containers
- Health checks on all services
- Named volumes for database persistence
- Proper networking (internal network for services)
- CI pipeline: lint, test, build, push for EACH service
- Secrets via environment variables, never baked into images

Respond ONLY with raw JSON:
{
  "files": [
    {"path": "docker-compose.yml", "content": "complete file content"},
    {"path": "services/user-service/Dockerfile", "content": "complete Dockerfile"}
  ]
}"""


class DevOpsAgent(ProductAgent):
    """Generates all DevOps/infrastructure files."""

    def __init__(self) -> None:
        super().__init__(
            name="devops",
            model=create_default_model(max_tokens=MAX_TOKENS_CODE),
            sys_prompt=SYS_PROMPT,
        )

    async def reply(self, msg: Msg | None = None) -> Msg:
        ctx = self.get_build_context(msg)
        architecture = ctx.get("architecture", {})

        print("\n" + "=" * 60)
        print("PHASE 8: DEVOPS & INFRASTRUCTURE")
        print("=" * 60)

        prompt = f"""Generate ALL infrastructure files for this architecture:

Architecture:
{json.dumps(architecture, indent=2)}

Generate:
1. Dockerfile for EVERY service and frontend
2. docker-compose.yml with ALL services, databases, queues
3. docker-compose.override.yml for local development
4. GitHub Actions CI/CD pipeline
5. Makefile with build/run/test/deploy commands
6. .env.example with ALL required environment variables
7. nginx.conf for API gateway routing (if applicable)
8. .dockerignore for each service"""

        result = await self.call_llm_json(prompt)
        files = result.get("files", [])

        print(f"\n  Generated {len(files)} infrastructure files:")
        for f in files:
            print(f"    - {f['path']}")

        all_files = ctx.get("all_files", {})
        for f in files:
            all_files[f["path"]] = f["content"]
        ctx["all_files"] = all_files

        return self.make_reply(f"Generated {len(files)} DevOps files", ctx)
