import json
from agents import (
    planner_agent,
    coder_agent,
    reviewer_agent,
    qa_agent,
    github_agent
)
from guardrails.guardrails_check import guard_input, guard_output
from core.gateway import gateway

class ProductBuilderOrchestrator:
    """
    Coordinates all agents with NeMo Guardrails security.
    Flow: Guard Input → Planner → Coder → Reviewer → QA → Guard Output → GitHub
    """

    def build(self, requirement: str) -> str:
        print("\n" + "="*60)
        print("AGENTSCOPE PRODUCT BUILDER")
        print("="*60)
        print(f"Building: {requirement}\n")

        # ── NeMo Input Guard ─────────────────────────────
        is_safe, reason = guard_input(requirement)
        if not is_safe:
            print(f"\n❌ Build blocked by security guardrail:")
            print(f"   Reason: {reason}")
            print("\nPlease provide a legitimate product requirement.")
            return None

        # ── Step 1: Plan ─────────────────────────────────
        plan = planner_agent.run(requirement)

        # ── Step 2: Code + Review + QA ───────────────────
        files = {}
        test_files = {}
        scores = []

        print(f"\n[Orchestrator] Processing {len(plan['files'])} files...\n")

        for file_info in plan["files"]:
            # Write
            code = coder_agent.run(requirement, plan, file_info)

            # Review
            review = reviewer_agent.run(file_info["path"], code, plan)
            scores.append(review.get("score", 70))

            # Use fixed code if needed
            final_code = review.get("fixed_code") or code
            files[file_info["path"]] = final_code

            status = "✅" if review["approved"] else "🔧 fixed"
            print(f"  {file_info['path']} {status} ({review.get('score',70)}/100)")

            # Tests
            test_code = qa_agent.run(
                requirement, plan, file_info["path"], final_code
            )
            if test_code:
                ext = "py" if plan["stack"] == "python" else "js"
                base = file_info["path"].replace("/","_").replace(".","_")
                test_files[f"tests/test_{base}.{ext}"] = test_code

        files.update(test_files)

        # ── NeMo Output Guard ────────────────────────────
        is_safe, clean_files = guard_output(plan, files)
        if not is_safe:
            print(f"\n❌ Output blocked by security guardrail")
            return None

        # ── Step 3: Push to GitHub ────────────────────────
        url = github_agent.run(plan, clean_files)

        # ── Summary ──────────────────────────────────────
        avg = sum(scores) / len(scores) if scores else 0
        usage = gateway.summary()  # ADD THIS LINE
        print("\n" + "="*60)
        print("BUILD COMPLETE!")
        print(f"Repo:        {url}")
        print(f"Files:       {len(clean_files)}")
        print(f"Tests:       {len(test_files)}")
        print(f"Avg quality: {avg:.0f}/100")
        print(f"API calls:   {usage['total_calls']}")      # ADD
        print(f"Tokens used: {usage['total_tokens']:,}")   # ADD
        print(f"Total cost:  {usage['total_cost']}")   
        print("="*60 + "\n")
        return url