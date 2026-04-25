"""Docs Agent — documentation generation using Haiku."""
import json
from agentscope.message import Msg
from agents.base import ProductAgent
from core.models import create_fast_model
from config.settings import MAX_TOKENS_DOCS

SYS_PROMPT = """You are a senior technical writer.
Generate comprehensive documentation for a multi-service product.

Generate these files:
1. README.md — project overview, architecture diagram (mermaid), setup, usage
2. docs/ARCHITECTURE.md — detailed architecture decisions, service boundaries
3. docs/API.md — complete API reference with examples
4. docs/SETUP.md — step-by-step local development setup
5. docs/DEPLOYMENT.md — deployment guide for production
6. docs/CONTRIBUTING.md — contribution guidelines
7. Each service gets its own README.md

Rules:
- Use Mermaid diagrams for architecture visualization
- Include curl examples for every API endpoint
- Step-by-step setup with prerequisites
- Troubleshooting section for common issues

Respond ONLY with raw JSON:
{
  "files": [
    {"path": "README.md", "content": "complete markdown content"},
    {"path": "docs/ARCHITECTURE.md", "content": "complete architecture docs"}
  ]
}"""


class DocsAgent(ProductAgent):
    """Generates all documentation files."""

    def __init__(self) -> None:
        super().__init__(
            name="docs",
            model=create_fast_model(max_tokens=MAX_TOKENS_DOCS),
            sys_prompt=SYS_PROMPT,
        )

    async def reply(self, msg: Msg | None = None) -> Msg:
        ctx = self.get_build_context(msg)
        architecture = ctx.get("architecture", {})
        api_contracts = ctx.get("api_contracts", {})
        db_schemas = ctx.get("db_schemas", {})
        parsed_prd = ctx.get("parsed_prd", {})

        print("\n" + "=" * 60)
        print("PHASE 9: DOCUMENTATION")
        print("=" * 60)

        prompt = f"""Generate complete documentation for this product:

Product: {parsed_prd.get('product_title', architecture.get('repo_name', 'project'))}
Description: {parsed_prd.get('product_description', '')}

Architecture:
{json.dumps(architecture, indent=2)[:3000]}

API Contracts:
{json.dumps(api_contracts, indent=2)[:3000]}

Database Schemas:
{json.dumps(db_schemas, indent=2)[:2000]}

Features:
{json.dumps(parsed_prd.get('core_features', []), indent=2)[:2000]}

Generate:
1. Root README.md with Mermaid architecture diagram
2. docs/ARCHITECTURE.md
3. docs/API.md with endpoint reference and curl examples
4. docs/SETUP.md with local development setup
5. docs/DEPLOYMENT.md
6. Individual README.md for each service"""

        result = await self.call_llm_json(prompt)
        files = result.get("files", [])

        print(f"\n  Generated {len(files)} documentation files:")
        for f in files:
            print(f"    - {f['path']}")

        all_files = ctx.get("all_files", {})
        for f in files:
            all_files[f["path"]] = f["content"]
        ctx["all_files"] = all_files

        return self.make_reply(f"Generated {len(files)} documentation files", ctx)
