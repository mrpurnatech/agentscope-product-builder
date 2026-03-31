from core.orchestrator import ProductBuilderOrchestrator


def main():
    print("\n" + "="*60)
    print("AGENTSCOPE PRODUCT BUILDER")
    print("="*60)
    requirement = input("What do you want to build? ")

    if not requirement.strip():
        print("Please describe your product.")
        return

    orchestrator = ProductBuilderOrchestrator()
    orchestrator.build(requirement)


if __name__ == "__main__":
    main()