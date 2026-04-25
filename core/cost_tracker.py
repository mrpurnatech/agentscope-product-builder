"""
CostTracker — singleton that tracks all LLM API usage across agents.

Replaces the old OpenClawGateway's cost tracking responsibility.
Model routing is now handled by assigning models at agent init time.
"""
from core.models import calculate_cost


class CostTracker:
    """Tracks API calls, token usage, and cost across all agents."""

    def __init__(self) -> None:
        self.call_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.per_agent: dict[str, dict] = {}

    def record(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        agent_name: str = "unknown",
    ) -> None:
        """Record a single LLM call."""
        cost = calculate_cost(model, input_tokens, output_tokens)

        self.call_count += 1
        self.total_tokens += input_tokens + output_tokens
        self.total_cost += cost

        # Per-agent tracking
        if agent_name not in self.per_agent:
            self.per_agent[agent_name] = {
                "calls": 0, "tokens": 0, "cost": 0.0
            }
        self.per_agent[agent_name]["calls"] += 1
        self.per_agent[agent_name]["tokens"] += input_tokens + output_tokens
        self.per_agent[agent_name]["cost"] += cost

        print(
            f"  [{agent_name}] {model.split('-')[1] if '-' in model else model} "
            f"| {input_tokens}+{output_tokens} tokens | ${cost:.4f}"
        )

    def summary(self) -> dict:
        """Return usage summary."""
        return {
            "total_calls": self.call_count,
            "total_tokens": self.total_tokens,
            "total_cost": f"${self.total_cost:.4f}",
            "per_agent": self.per_agent,
        }

    def reset(self) -> None:
        """Reset all counters."""
        self.call_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.per_agent.clear()


# Singleton — shared across all agents
cost_tracker = CostTracker()
