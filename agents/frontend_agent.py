"""Frontend Agent — multi-frontend app generation using Sonnet."""
import json
from agentscope.message import Msg
from agents.base import ProductAgent
from core.models import create_default_model
from config.settings import MAX_TOKENS_CODE

PLAN_SYS_PROMPT = """You are a senior frontend architect.
Given a frontend app specification and API contracts, plan ALL files needed.

Rules:
- Follow Next.js App Router conventions (app/ directory) for Next.js
- Follow React + Vite conventions for SPAs
- Use TypeScript throughout
- Use Tailwind CSS for styling
- Include proper component hierarchy (layouts, pages, components, hooks, lib)
- Include auth flow (login, register, protected routes)
- Include error boundaries and loading states

Respond ONLY with raw JSON:
{
  "name": "frontend-name",
  "stack": "nextjs|react",
  "files": [
    {"path": "src/app/layout.tsx", "purpose": "Root layout with providers"},
    {"path": "src/app/page.tsx", "purpose": "Landing/home page"}
  ],
  "packages": {
    "dependencies": {"next": "latest", "react": "^18"},
    "devDependencies": {"typescript": "^5", "@types/react": "^18"}
  }
}"""

CODE_SYS_PROMPT = """You are a senior frontend developer.
Write production-ready TypeScript/React code.

Rules:
- Complete implementation, no stubs or TODOs
- TypeScript strict mode — proper types, no 'any'
- Tailwind CSS for all styling (no CSS modules)
- Responsive design (mobile-first)
- Proper error handling with error boundaries
- Loading states and skeleton screens
- Accessible HTML (ARIA labels, semantic elements)
- React Query / SWR for data fetching
- Environment variables via NEXT_PUBLIC_ or VITE_ prefix

Return ONLY raw file content, no markdown, no explanation."""


class FrontendAgent(ProductAgent):
    """Plans and generates frontend application files."""

    def __init__(self) -> None:
        super().__init__(
            name="frontend",
            model=create_default_model(max_tokens=MAX_TOKENS_CODE),
            sys_prompt=CODE_SYS_PROMPT,
        )

    async def plan(
        self,
        frontend: dict,
        architecture: dict,
        api_contracts: dict,
    ) -> dict:
        """Plan all files for a frontend app."""
        print(f"\n  [frontend] Planning {frontend['name']}...")

        self.sys_prompt = PLAN_SYS_PROMPT
        prompt = f"""Plan all files for this frontend:

Frontend Spec:
{json.dumps(frontend, indent=2)}

API Contracts:
{json.dumps(api_contracts, indent=2)[:3000]}

Pages to implement:
{json.dumps(frontend.get('pages', []), indent=2)}"""

        plan_data = await self.call_llm_json(prompt)
        print(f"    Files planned: {len(plan_data.get('files', []))}")
        self.sys_prompt = CODE_SYS_PROMPT
        return plan_data

    async def generate_file(
        self,
        frontend: dict,
        frontend_plan: dict,
        file_info: dict,
        api_contracts: dict,
    ) -> str:
        """Generate code for a single frontend file."""
        print(f"    [frontend] Writing {file_info['path']}...")

        all_files = [f["path"] for f in frontend_plan.get("files", [])]
        prompt = f"""Project: {frontend.get('description', frontend['name'])}
Stack: {frontend['stack']} / TypeScript / Tailwind CSS
Packages: {json.dumps(frontend_plan.get('packages', {}).get('dependencies', {}))}

API Base URL: Use environment variable (NEXT_PUBLIC_API_URL or VITE_API_URL)
Auth: JWT Bearer token

All project files: {json.dumps(all_files)}

API Endpoints Available:
{json.dumps(api_contracts.get('services', []), indent=2)[:3000]}

Write complete production code for:
Path: {file_info['path']}
Purpose: {file_info['purpose']}"""

        return await self.call_llm(prompt)

    async def reply(self, msg: Msg | None = None) -> Msg:
        ctx = self.get_build_context(msg)
        return self.make_reply("Frontend ready", ctx)
