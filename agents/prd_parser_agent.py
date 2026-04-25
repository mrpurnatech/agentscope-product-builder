"""PRD Parser Agent — deep requirement analysis using Opus."""
import json
from agentscope.message import Msg
from agents.base import ProductAgent
from core.models import create_smart_model
from config.settings import MAX_TOKENS_ARCHITECT

SYS_PROMPT = """You are an elite product strategist and requirements engineer.
You receive a Product Requirements Document (PRD) — from a single sentence
to a multi-page spec — and extract a deeply structured analysis.

Think step-by-step:
1. Identify the product's core value proposition
2. Break features into atomic user stories with acceptance criteria
3. Identify non-functional requirements (scale, security, performance)
4. Detect third-party integrations needed
5. Identify data entities and their relationships
6. Determine the target user personas
7. Flag ambiguities or missing requirements (fill with smart defaults)

Respond ONLY with raw JSON:
{
  "product_name": "kebab-case-name",
  "product_title": "Human Readable Title",
  "product_description": "2-3 sentence description",
  "target_users": [
    {"persona": "name", "description": "who they are", "needs": ["need1"]}
  ],
  "core_features": [
    {
      "id": "F1",
      "name": "Feature Name",
      "description": "What it does",
      "module": "which service/module owns this",
      "priority": "P0|P1|P2",
      "user_stories": ["As a [persona] I want [action] so that [benefit]"],
      "acceptance_criteria": ["Given [context] When [action] Then [result]"],
      "data_entities": ["User", "Order"],
      "api_endpoints": ["POST /api/users", "GET /api/orders"]
    }
  ],
  "data_model": {
    "entities": [
      {
        "name": "User",
        "fields": [
          {"name": "id", "type": "uuid", "constraints": "primary key"},
          {"name": "email", "type": "string", "constraints": "unique, required"}
        ],
        "relationships": [
          {"to": "Order", "type": "one-to-many", "foreign_key": "user_id"}
        ]
      }
    ]
  },
  "integrations": [
    {"name": "Stripe", "purpose": "Payment processing", "apis_used": ["Checkout", "Webhooks"]}
  ],
  "non_functional": {
    "scalability": "Expected load and growth",
    "security": "Auth method, data protection needs",
    "performance": "Response time, throughput targets",
    "compliance": "GDPR, SOC2, etc. or none"
  },
  "tech_preferences": {
    "backend": "any preference mentioned or null",
    "frontend": "any preference mentioned or null",
    "database": "any preference mentioned or null",
    "hosting": "any preference mentioned or null"
  },
  "ambiguities_resolved": [
    {"question": "What was unclear", "default_chosen": "What we assumed"}
  ]
}

Be exhaustive. A 1-line requirement should produce 5-10 features."""


class PRDParserAgent(ProductAgent):
    """Parses a PRD into structured product requirements."""

    def __init__(self) -> None:
        super().__init__(
            name="prd_parser",
            model=create_smart_model(max_tokens=MAX_TOKENS_ARCHITECT),
            sys_prompt=SYS_PROMPT,
        )

    async def reply(self, msg: Msg | None = None) -> Msg:
        prd_text = msg.get_text_content() if msg else ""
        ctx = self.get_build_context(msg)

        print("\n" + "=" * 60)
        print("PHASE 1: PRD ANALYSIS")
        print("=" * 60)
        print(f"  Analyzing: {prd_text[:80]}...")

        parsed = await self.call_llm_json(
            f"Product Requirements Document:\n\n{prd_text}"
        )

        features = parsed.get("core_features", [])
        entities = parsed.get("data_model", {}).get("entities", [])
        integrations = parsed.get("integrations", [])

        print(f"\n  Product:      {parsed.get('product_title', 'Unknown')}")
        print(f"  Features:     {len(features)} ({sum(1 for f in features if f.get('priority') == 'P0')} P0)")
        print(f"  Entities:     {len(entities)}")
        print(f"  Integrations: {len(integrations)}")

        ctx["parsed_prd"] = parsed
        return self.make_reply(
            f"PRD parsed: {parsed.get('product_title', 'Unknown')} — "
            f"{len(features)} features, {len(entities)} entities",
            ctx,
        )
