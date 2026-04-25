# CLAUDE.md — AgentScope Product Builder

## Project Overview
Fully automated multi-agent product factory built on **AgentScope 1.0.18**.
Takes a PRD (from a single sentence to a full spec) and produces a complete
production-ready multi-service codebase with frontends, infrastructure, and
documentation — pushed to GitHub.

All 13 agents are proper `AgentBase` subclasses communicating via `Msg` objects,
orchestrated with `SequentialPipeline` and `FanoutPipeline`.

## Multi-Agent Architecture

### Agent Communication Flow
```
User PRD (Msg)
  │
  ▼ SequentialPipeline (Design)
  PRDParserAgent ──Msg──▶ ArchitectAgent ──Msg──▶ DatabaseAgent ──Msg──▶ APIDesignerAgent
       (Opus)                (Opus)              (Sonnet)              (Sonnet)
  │
  ▼ FanoutPipeline (parallel per service)
  PlannerAgent → [CoderAgent → ReviewerAgent → QAAgent] per file
     (Sonnet)      (Sonnet)      (Haiku)       (Haiku)
  │
  ▼ FanoutPipeline (parallel per frontend)
  FrontendAgent (plan + generate)
     (Sonnet)
  │
  ▼ SequentialPipeline (Infrastructure)
  IntegrationAgent ──Msg──▶ DevOpsAgent ──Msg──▶ DocsAgent
      (Sonnet)                (Sonnet)           (Haiku)
  │
  ▼ GuardRails → GitHubAgent (push)
```

### Build Context (Msg.metadata)
Agents pass accumulated state via `Msg.metadata["build_context"]`:
```python
{
  "parsed_prd":    {...},  # PRD Parser output
  "architecture":  {...},  # Architect output
  "db_schemas":    {...},  # Database Agent output
  "api_contracts": {...},  # API Designer output
  "all_files":     {...},  # Accumulated {path: content}
  "repo_url":      "...",  # GitHub Agent output
}
```

### 13 Agents
| Agent | Class | File | Model Tier | AgentScope Role |
|-------|-------|------|-----------|-----------------|
| PRD Parser | `PRDParserAgent` | `agents/prd_parser_agent.py` | smart (Opus) | Design phase |
| Architect | `ArchitectAgent` | `agents/architect_agent.py` | smart (Opus) | Design phase |
| Database | `DatabaseAgent` | `agents/database_agent.py` | default (Sonnet) | Design phase |
| API Designer | `APIDesignerAgent` | `agents/api_designer_agent.py` | default (Sonnet) | Design phase |
| Planner | `PlannerAgent` | `agents/planner_agent.py` | default (Sonnet) | Build phase |
| Coder | `CoderAgent` | `agents/coder_agent.py` | default (Sonnet) | Build phase |
| Reviewer | `ReviewerAgent` | `agents/reviewer_agent.py` | fast (Haiku) | Build phase |
| QA | `QAAgent` | `agents/qa_agent.py` | fast (Haiku) | Build phase |
| Frontend | `FrontendAgent` | `agents/frontend_agent.py` | default (Sonnet) | Build phase |
| Integration | `IntegrationAgent` | `agents/integration_agent.py` | default (Sonnet) | Infra phase |
| DevOps | `DevOpsAgent` | `agents/devops_agent.py` | default (Sonnet) | Infra phase |
| Docs | `DocsAgent` | `agents/docs_agent.py` | fast (Haiku) | Infra phase |
| GitHub | `GitHubAgent` | `agents/github_agent.py` | none (API only) | Ship phase |

### Core Modules
| Module | File | Purpose |
|--------|------|---------|
| Base Agent | `agents/base.py` | `ProductAgent(AgentBase)` — LLM helpers, context management |
| Models | `core/models.py` | `AnthropicChatModel` factory (3 tiers) |
| Cost Tracker | `core/cost_tracker.py` | Singleton tracking all API usage |
| Orchestrator | `core/orchestrator.py` | Pipeline composition + async build |
| Guardrails | `guardrails/guardrails_check.py` | Input/output security checks |
| Settings | `config/settings.py` | Env vars, model names, token limits |

## Code Conventions
- All agents extend `ProductAgent(AgentBase)` — proper AgentScope agents
- Agent communication via `Msg` objects with `metadata["build_context"]`
- `reply(msg)` is the main agent entry point (called by pipelines)
- Direct methods (`plan_service()`, `generate()`, `review()`) for fine-grained control
- `SequentialPipeline` for dependent phases, `FanoutPipeline` / `asyncio.gather` for parallel
- Models created via `create_fast_model()`, `create_default_model()`, `create_smart_model()`
- Cost tracked via `core.cost_tracker.cost_tracker` singleton
- All agent operations are `async` — entire pipeline is async

## Development Rules
- New agents MUST extend `ProductAgent` from `agents/base.py`
- Use `self.call_llm()` / `self.call_llm_json()` — never call anthropic directly
- Store structured output in `Msg.metadata["build_context"]`
- Return `self.make_reply(content, ctx)` from `reply()`
- Keep agents stateless within a single call — state flows through Msg metadata
- Input guardrails run before any LLM call; output guardrails before GitHub push

## Common Tasks
```bash
# Run CLI (interactive PRD input)
python main.py

# Run CLI (inline PRD)
python main.py "A SaaS invoicing app with Stripe payments"

# Run Telegram bot
python telegram_bot.py

# Run tests
pytest tests/ -v

# Install deps
pip install -r requirements.txt
```

## Generated Monorepo Structure
```
repo-name/
├── services/
│   ├── api-gateway/        # routing, auth, rate limiting
│   ├── user-service/       # user management
│   └── ...
├── apps/
│   ├── web-app/            # Next.js frontend
│   ├── admin-dashboard/    # React admin panel
│   └── ...
├── shared/                 # types, clients, middleware
├── docker-compose.yml
├── .github/workflows/ci.yml
├── README.md
└── docs/
```
