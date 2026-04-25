"""
ProductBuilderOrchestrator — async multi-agent pipeline using AgentScope.

Pipeline:
  Phase 1-4: Design Pipeline    (SequentialPipeline)
    PRD Parser → Architect → Database → API Designer

  Phase 5: Service Builds       (FanoutPipeline per service)
    For each service: Planner → [Coder → Reviewer → QA] per file

  Phase 6: Frontend Builds      (FanoutPipeline)
    For each frontend: Plan → Generate all files

  Phase 7-9: Infrastructure Pipeline (SequentialPipeline)
    Integration → DevOps → Docs

  Ship: GitHub Push
"""
import asyncio
import json

from agentscope.message import Msg
from agentscope.pipeline import SequentialPipeline, FanoutPipeline

from agents.prd_parser_agent import PRDParserAgent
from agents.architect_agent import ArchitectAgent
from agents.database_agent import DatabaseAgent
from agents.api_designer_agent import APIDesignerAgent
from agents.planner_agent import PlannerAgent
from agents.coder_agent import CoderAgent
from agents.reviewer_agent import ReviewerAgent
from agents.qa_agent import QAAgent
from agents.frontend_agent import FrontendAgent
from agents.integration_agent import IntegrationAgent
from agents.devops_agent import DevOpsAgent
from agents.docs_agent import DocsAgent
from agents.github_agent import GitHubAgent

from guardrails.guardrails_check import guard_input, guard_output
from core.cost_tracker import cost_tracker


class ProductBuilderOrchestrator:
    """
    Fully automated multi-agent product builder.

    Uses AgentScope pipelines for agent orchestration:
    - SequentialPipeline for dependent phases
    - FanoutPipeline for parallel service/frontend builds
    - Direct agent calls for fine-grained control (code→review→test loop)
    """

    def __init__(self) -> None:
        # ── Design agents (sequential) ────────────────────
        self.prd_parser = PRDParserAgent()
        self.architect = ArchitectAgent()
        self.database = DatabaseAgent()
        self.api_designer = APIDesignerAgent()

        # ── Build agents (per-service, reusable) ──────────
        self.planner = PlannerAgent()
        self.coder = CoderAgent()
        self.reviewer = ReviewerAgent()
        self.qa = QAAgent()
        self.frontend = FrontendAgent()

        # ── Infrastructure agents (sequential) ────────────
        self.integration = IntegrationAgent()
        self.devops = DevOpsAgent()
        self.docs = DocsAgent()

        # ── Ship agent ────────────────────────────────────
        self.github = GitHubAgent()

        # ── Design pipeline: PRD → Architect → DB → API ──
        self.design_pipeline = SequentialPipeline(
            agents=[self.prd_parser, self.architect, self.database, self.api_designer]
        )

        # ── Infra pipeline: Integration → DevOps → Docs ──
        self.infra_pipeline = SequentialPipeline(
            agents=[self.integration, self.devops, self.docs]
        )

    async def build(self, prd: str) -> str:
        """Run the full multi-agent pipeline. Returns GitHub repo URL."""
        print("\n" + "=" * 60)
        print("  AGENTSCOPE PRODUCT BUILDER")
        print("  Multi-Agent Pipeline (AgentScope)")
        print("=" * 60)
        print(f"\nPRD: {prd[:100]}{'...' if len(prd) > 100 else ''}\n")

        # ── Input guardrails ──────────────────────────────
        is_safe, reason = guard_input(prd)
        if not is_safe:
            print(f"\n[BLOCKED] {reason}")
            return None

        # ══════════════════════════════════════════════════
        # PHASES 1-4: DESIGN PIPELINE (Sequential)
        # PRD → Architecture → Database → API Contracts
        # ══════════════════════════════════════════════════
        initial_msg = Msg(
            name="user",
            content=prd,
            role="user",
            metadata={"build_context": {}},
        )

        design_result = await self.design_pipeline(initial_msg)
        ctx = design_result.metadata.get("build_context", {})

        architecture = ctx.get("architecture", {})
        db_schemas = ctx.get("db_schemas", {})
        api_contracts = ctx.get("api_contracts", {})
        parsed_prd = ctx.get("parsed_prd", {})

        # Initialize all_files in context
        ctx.setdefault("all_files", {})

        # ══════════════════════════════════════════════════
        # PHASE 5: BUILD BACKEND SERVICES (Parallel per service)
        # ══════════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("PHASE 5: BUILD BACKEND SERVICES")
        print("=" * 60)

        services = architecture.get("services", [])
        if services:
            # Build all services concurrently
            service_tasks = [
                self._build_service(service, architecture, db_schemas, api_contracts, parsed_prd)
                for service in services
            ]
            service_results = await asyncio.gather(*service_tasks)

            # Merge all service files into context
            for files in service_results:
                ctx["all_files"].update(files)

        # ══════════════════════════════════════════════════
        # PHASE 6: BUILD FRONTENDS (Parallel per frontend)
        # ══════════════════════════════════════════════════
        print("\n" + "=" * 60)
        print("PHASE 6: BUILD FRONTENDS")
        print("=" * 60)

        frontends = architecture.get("frontends", [])
        if frontends:
            frontend_tasks = [
                self._build_frontend(fe, architecture, api_contracts)
                for fe in frontends
            ]
            frontend_results = await asyncio.gather(*frontend_tasks)

            for files in frontend_results:
                ctx["all_files"].update(files)
        else:
            print("  No frontend apps in architecture.")

        # ══════════════════════════════════════════════════
        # PHASES 7-9: INFRASTRUCTURE PIPELINE (Sequential)
        # Integration → DevOps → Docs
        # ══════════════════════════════════════════════════
        infra_msg = Msg(
            name="orchestrator",
            content="Generate infrastructure",
            role="user",
            metadata={"build_context": ctx},
        )
        infra_result = await self.infra_pipeline(infra_msg)
        ctx = infra_result.metadata.get("build_context", ctx)

        all_files = ctx.get("all_files", {})

        # ── Output guardrails ─────────────────────────────
        plan_meta = {
            "repo_name": architecture.get("repo_name", parsed_prd.get("product_name", "project")),
            "description": architecture.get("description", ""),
            "private": False,
        }
        is_safe, clean_files = guard_output(plan_meta, all_files)
        if not is_safe:
            print("\n[BLOCKED] Output guardrails failed.")
            return None

        # ── Ship to GitHub ────────────────────────────────
        url = await self.github.push(plan_meta, clean_files)

        # ── Build summary ─────────────────────────────────
        usage = cost_tracker.summary()

        print("\n" + "=" * 60)
        print("  BUILD COMPLETE!")
        print("=" * 60)
        print(f"  Repo:       {url}")
        print(f"  Services:   {len(services)}")
        print(f"  Frontends:  {len(frontends)}")
        print(f"  Total files:{len(clean_files)}")
        print(f"  API calls:  {usage['total_calls']}")
        print(f"  Tokens:     {usage['total_tokens']:,}")
        print(f"  Cost:       {usage['total_cost']}")
        print("=" * 60 + "\n")

        return url

    async def _build_service(
        self,
        service: dict,
        architecture: dict,
        db_schemas: dict,
        api_contracts: dict,
        parsed_prd: dict,
    ) -> dict:
        """Build a single backend service: plan → code → review → test per file."""
        service_name = service["name"]
        files = {}

        # Plan the service
        plan = await self.planner.plan_service(
            service, architecture, db_schemas, api_contracts
        )

        plan_files = plan.get("files", [])
        print(f"\n  [{service_name}] Building {len(plan_files)} files...")

        # Build context for the coder
        service_context = self._make_service_context(
            service, architecture, db_schemas, api_contracts, parsed_prd
        )

        for file_info in plan_files:
            # Code
            code = await self.coder.generate(service_context, plan, file_info)

            # Review
            review = await self.reviewer.review(file_info["path"], code, plan)
            final_code = review.get("fixed_code") or code
            score = review.get("score", 70)

            full_path = f"services/{service_name}/{file_info['path']}"
            files[full_path] = final_code

            status = "pass" if review.get("approved", True) else "fixed"
            print(f"    {file_info['path']} [{status}] ({score}/100)")

            # Tests
            test_code = await self.qa.generate_tests(
                service_context, plan, file_info["path"], final_code
            )
            if test_code:
                ext = "py" if service["stack"] == "python" else "js"
                base = file_info["path"].replace("/", "_").replace(".", "_")
                files[f"services/{service_name}/tests/test_{base}.{ext}"] = test_code

        print(f"  [{service_name}] Done: {len(files)} files")
        return files

    async def _build_frontend(
        self,
        frontend: dict,
        architecture: dict,
        api_contracts: dict,
    ) -> dict:
        """Build a single frontend app: plan → generate all files."""
        frontend_name = frontend["name"]
        files = {}

        # Plan
        frontend_plan = await self.frontend.plan(
            frontend, architecture, api_contracts
        )

        plan_files = frontend_plan.get("files", [])
        print(f"  [{frontend_name}] Building {len(plan_files)} files...")

        for file_info in plan_files:
            code = await self.frontend.generate_file(
                frontend, frontend_plan, file_info, api_contracts
            )
            files[f"apps/{frontend_name}/{file_info['path']}"] = code

        # Generate package.json
        packages = frontend_plan.get("packages", {})
        if packages:
            scripts = {
                "dev": "next dev" if frontend["stack"] == "nextjs" else "vite",
                "build": "next build" if frontend["stack"] == "nextjs" else "vite build",
                "start": "next start" if frontend["stack"] == "nextjs" else "vite preview",
                "lint": "next lint" if frontend["stack"] == "nextjs" else "eslint src/",
            }
            pkg = {
                "name": frontend_name,
                "version": "0.1.0",
                "private": True,
                "scripts": scripts,
                "dependencies": packages.get("dependencies", {}),
                "devDependencies": packages.get("devDependencies", {}),
            }
            files[f"apps/{frontend_name}/package.json"] = json.dumps(pkg, indent=2)

        print(f"  [{frontend_name}] Done: {len(files)} files")
        return files

    @staticmethod
    def _make_service_context(
        service: dict,
        architecture: dict,
        db_schemas: dict,
        api_contracts: dict,
        parsed_prd: dict,
    ) -> str:
        """Build a rich context string for the coder agent."""
        service_schema = next(
            (s for s in db_schemas.get("schemas", []) if s["service"] == service["name"]),
            None,
        )
        service_api = next(
            (s for s in api_contracts.get("services", []) if s["service"] == service["name"]),
            None,
        )

        parts = [
            f"Product: {parsed_prd.get('product_title', 'Product')}",
            f"Service: {service['name']} — {service.get('description', '')}",
            f"Features: {', '.join(service.get('owns_features', []))}",
        ]
        if service_schema:
            tables = [t["name"] for t in service_schema.get("tables", [])]
            parts.append(f"Database tables: {', '.join(tables)}")
        if service_api:
            endpoints = [
                f"{e['method']} {e['path']}"
                for e in service_api.get("endpoints", [])[:10]
            ]
            parts.append(f"API endpoints: {', '.join(endpoints)}")

        return "\n".join(parts)
