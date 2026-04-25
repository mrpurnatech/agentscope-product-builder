"""Architect Agent — multi-service architecture design using Opus."""
import json
from agentscope.message import Msg
from agents.base import ProductAgent
from core.models import create_smart_model
from config.settings import MAX_TOKENS_ARCHITECT

SYS_PROMPT = """You are a principal software architect with 20 years experience
designing distributed systems at FAANG scale.

Given parsed product requirements, design the COMPLETE multi-service architecture.

Design principles:
1. Service boundaries follow domain boundaries (DDD)
2. Each service owns its data — no shared databases
3. API Gateway handles routing, auth, rate limiting
4. Use event-driven patterns for cross-service communication where appropriate
5. Every service is independently deployable
6. Frontend apps are separate deployable units
7. Shared types/contracts live in a shared package

Choose the BEST stack for each service:
- Python/FastAPI: Data-heavy, ML, analytics, complex business logic
- Node.js/Express: Real-time, I/O heavy, webhooks, lightweight APIs
- Next.js: Full-stack web apps with SSR, SEO needs
- React: SPAs, dashboards, admin panels

Respond ONLY with raw JSON:
{
  "repo_name": "kebab-case-name",
  "description": "one-line repo description",
  "architecture_type": "microservices",
  "services": [
    {
      "name": "service-name",
      "type": "gateway|backend|worker|shared",
      "stack": "python|nodejs",
      "framework": "fastapi|express",
      "port": 8000,
      "description": "What this service does",
      "owns_features": ["F1", "F2"],
      "dependencies": ["other-service-name"],
      "database": {"type": "postgres|mongodb|redis|none", "name": "db_name"},
      "message_queue": {
        "publishes": ["user.created"],
        "subscribes": ["payment.confirmed"]
      },
      "environment_vars": ["DATABASE_URL=postgresql://...", "JWT_SECRET=secret"],
      "packages": ["fastapi", "sqlalchemy", "pydantic"]
    }
  ],
  "frontends": [
    {
      "name": "frontend-name",
      "type": "web-app|admin-dashboard|landing-page",
      "stack": "nextjs|react",
      "framework": "nextjs|react+vite",
      "port": 3000,
      "description": "What this frontend does",
      "owns_features": ["F1", "F3"],
      "connects_to": ["api-gateway"],
      "pages": [
        {"path": "/", "name": "Home", "description": "Landing page"}
      ],
      "packages": ["next", "tailwindcss", "shadcn-ui", "axios"]
    }
  ],
  "shared": {
    "name": "shared-types",
    "types": ["User", "Order", "ApiResponse"],
    "utils": ["auth", "validation", "errors"]
  },
  "infrastructure": {
    "api_gateway": {
      "enabled": true,
      "routes": [
        {"path": "/api/users/*", "service": "user-service", "port": 8001}
      ]
    },
    "message_queue": "redis|rabbitmq|none",
    "cache": "redis|none",
    "docker": true,
    "ci_cd": "github-actions",
    "monitoring": "prometheus+grafana|none"
  },
  "deployment": {
    "strategy": "docker-compose|kubernetes",
    "environments": ["development", "staging", "production"]
  }
}

Design for PRODUCTION. Not a toy."""


class ArchitectAgent(ProductAgent):
    """Designs multi-service architecture from parsed PRD."""

    def __init__(self) -> None:
        super().__init__(
            name="architect",
            model=create_smart_model(max_tokens=MAX_TOKENS_ARCHITECT),
            sys_prompt=SYS_PROMPT,
        )

    async def reply(self, msg: Msg | None = None) -> Msg:
        ctx = self.get_build_context(msg)
        parsed_prd = ctx.get("parsed_prd", {})

        print("\n" + "=" * 60)
        print("PHASE 2: ARCHITECTURE DESIGN")
        print("=" * 60)

        prompt = f"""Design the complete multi-service architecture for this product:

Product: {parsed_prd.get('product_title', 'Unknown')}
Description: {parsed_prd.get('product_description', '')}

Features:
{json.dumps(parsed_prd.get('core_features', []), indent=2)}

Data Model:
{json.dumps(parsed_prd.get('data_model', {}), indent=2)}

Integrations:
{json.dumps(parsed_prd.get('integrations', []), indent=2)}

Non-functional Requirements:
{json.dumps(parsed_prd.get('non_functional', {}), indent=2)}

Tech Preferences:
{json.dumps(parsed_prd.get('tech_preferences', {}), indent=2)}"""

        arch = await self.call_llm_json(prompt)

        services = arch.get("services", [])
        frontends = arch.get("frontends", [])

        print(f"\n  Architecture: {arch.get('architecture_type', 'unknown')}")
        print(f"  Services:     {len(services)}")
        for s in services:
            db = s.get("database", {}).get("type", "none")
            print(f"    - {s['name']} ({s['stack']}/{s['framework']}) :{s['port']} [db:{db}]")
        print(f"  Frontends:    {len(frontends)}")
        for f in frontends:
            print(f"    - {f['name']} ({f['stack']}) :{f['port']}")

        ctx["architecture"] = arch
        return self.make_reply(
            f"Architecture: {len(services)} services, {len(frontends)} frontends",
            ctx,
        )
