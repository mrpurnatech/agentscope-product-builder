"""Database Agent — schema design per service using Sonnet."""
import json
from agentscope.message import Msg
from agents.base import ProductAgent
from core.models import create_default_model
from config.settings import MAX_TOKENS_CODE

SYS_PROMPT = """You are a senior database architect.
Given the architecture and data model, produce complete database schemas
for each service that owns a database.

Rules:
- Each service gets its own isolated schema
- Use proper data types, constraints, indexes
- Include created_at/updated_at timestamps on all tables
- Include soft-delete (deleted_at) where appropriate
- Design for the specific database type (PostgreSQL vs MongoDB)
- Include junction tables for many-to-many relationships
- Add indexes on foreign keys and frequently queried columns
- Include seed data / initial migration

Respond ONLY with raw JSON:
{
  "schemas": [
    {
      "service": "service-name",
      "database_type": "postgres|mongodb",
      "database_name": "db_name",
      "tables": [
        {
          "name": "users",
          "columns": [
            {"name": "id", "type": "UUID", "constraints": "PRIMARY KEY DEFAULT gen_random_uuid()"}
          ],
          "indexes": [
            {"name": "idx_users_email", "columns": ["email"], "unique": true}
          ]
        }
      ],
      "migrations": [
        {"version": "001", "name": "initial_schema", "up_sql": "CREATE TABLE ...", "down_sql": "DROP TABLE ..."}
      ],
      "orm_models": "complete ORM model code (SQLAlchemy for Python, Prisma for Node.js)"
    }
  ]
}"""


class DatabaseAgent(ProductAgent):
    """Designs database schemas for all services with databases."""

    def __init__(self) -> None:
        super().__init__(
            name="database",
            model=create_default_model(max_tokens=MAX_TOKENS_CODE),
            sys_prompt=SYS_PROMPT,
        )

    async def reply(self, msg: Msg | None = None) -> Msg:
        ctx = self.get_build_context(msg)
        architecture = ctx.get("architecture", {})
        parsed_prd = ctx.get("parsed_prd", {})

        print("\n" + "=" * 60)
        print("PHASE 3: DATABASE DESIGN")
        print("=" * 60)

        services_with_db = [
            s for s in architecture.get("services", [])
            if s.get("database", {}).get("type", "none") != "none"
        ]

        if not services_with_db:
            print("  No services require a database.")
            ctx["db_schemas"] = {"schemas": []}
            return self.make_reply("No databases needed", ctx)

        prompt = f"""Design complete database schemas for this architecture:

Services with databases:
{json.dumps(services_with_db, indent=2)}

Data Model from PRD:
{json.dumps(parsed_prd.get('data_model', {}), indent=2)}

Features:
{json.dumps(parsed_prd.get('core_features', []), indent=2)}

Design schemas for ALL services that have a database."""

        schemas = await self.call_llm_json(prompt)

        for schema in schemas.get("schemas", []):
            tables = schema.get("tables", [])
            print(f"  {schema['service']} ({schema['database_type']}): {len(tables)} tables")

        ctx["db_schemas"] = schemas
        return self.make_reply(
            f"Designed {len(schemas.get('schemas', []))} database schemas",
            ctx,
        )
