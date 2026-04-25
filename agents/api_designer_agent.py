"""API Designer Agent — REST contract design using Sonnet."""
import json
from agentscope.message import Msg
from agents.base import ProductAgent
from core.models import create_default_model
from config.settings import MAX_TOKENS_CODE

SYS_PROMPT = """You are a senior API architect.
Design complete REST API contracts for all services.

Rules:
- RESTful resource naming (plural nouns, kebab-case)
- Proper HTTP methods (GET, POST, PUT, PATCH, DELETE)
- Consistent response envelope: {"data": ..., "error": null, "meta": {...}}
- Pagination: cursor-based for large datasets, offset for small
- Authentication: JWT Bearer tokens
- Rate limiting headers
- Proper HTTP status codes (201 for creation, 204 for deletion)
- Request validation with detailed error messages
- API versioning via URL prefix (/api/v1/...)
- Inter-service communication contracts (internal APIs)

Respond ONLY with raw JSON:
{
  "api_version": "v1",
  "base_path": "/api/v1",
  "auth": {
    "type": "jwt",
    "endpoints": {
      "login": "POST /api/v1/auth/login",
      "register": "POST /api/v1/auth/register",
      "refresh": "POST /api/v1/auth/refresh"
    },
    "header": "Authorization: Bearer <token>"
  },
  "services": [
    {
      "service": "service-name",
      "base_url": "http://service-name:port",
      "endpoints": [
        {
          "method": "POST",
          "path": "/api/v1/users",
          "description": "Create a new user",
          "auth_required": true,
          "roles": ["admin"],
          "request_body": {"email": "string (required)"},
          "response": {"status": 201, "body": {"data": {"id": "uuid"}, "error": null}},
          "errors": [{"status": 400, "message": "Validation error"}]
        }
      ]
    }
  ],
  "internal_apis": [
    {"from": "order-service", "to": "user-service", "endpoint": "GET /internal/users/:id", "purpose": "Validate user exists"}
  ],
  "webhooks": [
    {"event": "payment.completed", "payload": {"order_id": "uuid"}, "target_service": "order-service"}
  ],
  "shared_types": {
    "PaginatedResponse": {"data": "T[]", "meta": {"total": "number", "page": "number"}},
    "ErrorResponse": {"data": null, "error": {"code": "string", "message": "string"}}
  }
}"""


class APIDesignerAgent(ProductAgent):
    """Designs API contracts for all services."""

    def __init__(self) -> None:
        super().__init__(
            name="api_designer",
            model=create_default_model(max_tokens=MAX_TOKENS_CODE),
            sys_prompt=SYS_PROMPT,
        )

    async def reply(self, msg: Msg | None = None) -> Msg:
        ctx = self.get_build_context(msg)
        architecture = ctx.get("architecture", {})
        db_schemas = ctx.get("db_schemas", {})

        print("\n" + "=" * 60)
        print("PHASE 4: API CONTRACT DESIGN")
        print("=" * 60)

        prompt = f"""Design complete REST API contracts for this architecture:

Architecture:
{json.dumps(architecture, indent=2)}

Database Schemas:
{json.dumps(db_schemas, indent=2)}

Design endpoints for ALL services."""

        contracts = await self.call_llm_json(prompt)

        total_endpoints = sum(
            len(svc.get("endpoints", []))
            for svc in contracts.get("services", [])
        )
        print(f"\n  Total endpoints:  {total_endpoints}")
        print(f"  Internal APIs:    {len(contracts.get('internal_apis', []))}")
        print(f"  Webhooks:         {len(contracts.get('webhooks', []))}")

        ctx["api_contracts"] = contracts
        return self.make_reply(
            f"Designed {total_endpoints} API endpoints",
            ctx,
        )
