import json
from agents import (
    planner_agent,
    coder_agent,
    reviewer_agent,
    qa_agent,
    github_agent
)


class ProductBuilderOrchestrator:
    """
    Coordinates all agents to build a complete product.
    Flow: Planner → Coder → Reviewer → QA → GitHub
    """

    def build(self, requirement: str) -> str:
        print("\n" + "="*60)
        print("AGENTSCOPE PRODUCT BUILDER")
        print("="*60)
        print(f"Building: {requirement}\n")

        # Step 1 — Plan
        plan = planner_agent.run(requirement)

        # Step 2 — Code + Review + QA per file
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
                base = file_info["path"].replace("/", "_").replace(".", "_")
                test_files[f"tests/test_{base}.{ext}"] = test_code

        files.update(test_files)

        # Step 3 — Push
        url = github_agent.run(plan, files)

        # Summary
        avg = sum(scores) / len(scores) if scores else 0
        print("\n" + "="*60)
        print("BUILD COMPLETE!")
        print(f"Repo:        {url}")
        print(f"Files:       {len(files)}")
        print(f"Tests:       {len(test_files)}")
        print(f"Avg quality: {avg:.0f}/100")
        print("="*60 + "\n")
        return url