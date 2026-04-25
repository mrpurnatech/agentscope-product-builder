import sys
import asyncio
import agentscope
from core.orchestrator import ProductBuilderOrchestrator


async def run():
    # Initialize AgentScope
    agentscope.init(
        project="agentscope-product-builder",
        logging_path="./logs",
        logging_level="INFO",
    )

    print("\n" + "=" * 60)
    print("  AGENTSCOPE PRODUCT BUILDER")
    print("  Multi-Agent Automated Product Factory")
    print("=" * 60)

    # Accept PRD from argument, stdin, or interactive prompt
    if len(sys.argv) > 1:
        prd = " ".join(sys.argv[1:])
    else:
        print("\nDescribe your product (PRD). For multi-line input,")
        print("type your requirements and press Enter twice when done.\n")

        lines = []
        empty_count = 0
        while True:
            try:
                line = input("> " if not lines else "  ")
                if line.strip() == "":
                    empty_count += 1
                    if empty_count >= 1 and lines:
                        break
                else:
                    empty_count = 0
                    lines.append(line)
            except EOFError:
                break

        prd = "\n".join(lines)

    if not prd.strip():
        print("Please describe your product.")
        return

    print(f"\nPRD received ({len(prd)} chars, {len(prd.split())} words)")

    orchestrator = ProductBuilderOrchestrator()
    url = await orchestrator.build(prd)

    if url:
        print(f"\nYour product is live at: {url}")
    else:
        print("\nBuild failed. Check the output above for details.")


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
