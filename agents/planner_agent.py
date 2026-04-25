"""Planner Agent — file-level planning per service using Sonnet."""
import json
from agentscope.message import Msg
from agents.base import ProductAgent
from core.models import create_default_model
from config.settings import MAX_TOKENS_PLAN

SYS_PROMPT = """You are a senior software architect.
Given a service specification within a larger multi-service architecture,
create a complete file-level plan for that service.

Rules:
- Include ALL files needed for a production service
- Follow framework best practices for directory structure
- Include: entry point, models, routes/controllers, services/business logic,
  middleware, config, utils, tests setup
- For Python/FastAPI: main.py, models/, routes/, services/, config/, middleware/
- For Node.js/Express: index.ts, models/, routes/, controllers/, services/, middleware/
- Include requirements.txt/package.json, Dockerfile, .env.example
- Include database migration files if service has a database

Respond ONLY with raw JSON:
{
  "service_name": "service-name",
  "stack": "python or nodejs",
  "framework": "fastapi or express",
  "description": "what this service does",
  "files": [
    {"path": "main.py", "purpose": "FastAPI application entry point"},
    {"path": "models/user.py", "purpose": "User SQLAlchemy model"}
  ],
  "dependencies": ["fastapi", "sqlalchemy", "pydantic"],
  "environment_vars": ["DATABASE_URL", "JWT_SECRET"]
}"""


class PlannerAgent(ProductAgent):
    """Plans file structure for a single service."""

    def __init__(self) -> None:
        super().__init__(
            name="planner",
            model=create_default_model(max_tokens=MAX_TOKENS_PLAN),
            sys_prompt=SYS_PROMPT,
        )

    async def plan_service(
        self,
        service: dict,
        architecture: dict,
        db_schemas: dict,
        api_contracts: dict,
    ) -> dict:
        """Plan all files for a single service. Returns plan dict."""
        print(f"\n  [planner] Planning service: {service['name']}...")

        # Find this service's DB schema and API contract
        service_schema = next(
            (s for s in db_schemas.get("schemas", []) if s["service"] == service["name"]),
            None,
        )
        service_api = next(
            (s for s in api_contracts.get("services", []) if s["service"] == service["name"]),
            None,
        )

        prompt = f"""Plan all files for this service:

Service:
{json.dumps(service, indent=2)}

Database Schema:
{json.dumps(service_schema, indent=2) if service_schema else 'No database'}

API Endpoints:
{json.dumps(service_api, indent=2) if service_api else 'No public API'}

Architecture Context:
- Architecture type: {architecture.get('architecture_type', 'microservices')}
- Other services: {[s['name'] for s in architecture.get('services', []) if s['name'] != service['name']]}
- Message queue: {architecture.get('infrastructure', {}).get('message_queue', 'none')}"""

        plan = await self.call_llm_json(prompt)
        print(f"    Files: {len(plan.get('files', []))}")
        return plan

    async def reply(self, msg: Msg | None = None) -> Msg:
        """Pipeline-compatible reply — plans the first un-planned service."""
        ctx = self.get_build_context(msg)
        return self.make_reply("Planner ready", ctx)
