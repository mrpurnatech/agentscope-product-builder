Add a new agent to the AgentScope pipeline.

Arguments: $ARGUMENTS (agent name and purpose, e.g. "docs_agent - generates README and API docs")

Steps:
1. Parse the agent name and purpose from $ARGUMENTS
2. Create `agents/<agent_name>.py` following the existing pattern:
   - Import `ask` and `parse_json` from `core.llm_client`
   - Define a `SYSTEM` prompt constant
   - Implement `def run(...)` as a stateless function
   - Use appropriate `task_type` for gateway routing
3. Add the import to `core/orchestrator.py`
4. Wire it into the pipeline at the correct position in `ProductBuilderOrchestrator.build()`
5. Update CLAUDE.md if the architecture description needs changes
