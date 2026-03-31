import time
import anthropic
import os
from typing import Optional
from config.settings import (
    ANTHROPIC_API_KEY,
    DEFAULT_MODEL,
    FAST_MODEL,
    SMART_MODEL
)

# ── Model tiers ───────────────────────────────────────────
TIERS = {
    "fast":    FAST_MODEL,    # claude-haiku-4-5
    "default": DEFAULT_MODEL, # claude-sonnet-4-6
    "smart":   SMART_MODEL,   # claude-opus-4-6
}

# ── Task routing rules ────────────────────────────────────
# Maps task types to appropriate model tier
ROUTING_RULES = {
    # Use Haiku — cheap, fast, good enough
    "review":    "fast",
    "qa":        "fast",
    "validate":  "fast",
    "classify":  "fast",
    "format":    "fast",

    # Use Sonnet — balanced cost and quality
    "code":      "default",
    "plan":      "default",
    "generate":  "default",
    "refactor":  "default",

    # Use Opus — maximum intelligence
    "architect": "smart",
    "security":  "smart",
    "complex":   "smart",
}

# ── Fallback chain ────────────────────────────────────────
# If primary model fails, try these in order
FALLBACK_CHAIN = {
    "smart":   ["smart", "default", "fast"],
    "default": ["default", "fast"],
    "fast":    ["fast", "default"],
}


class OpenClawGateway:
    """
    Central gateway for all LLM calls.
    Handles routing, rate limits, retries, and fallbacks.
    """

    def __init__(self):
        self.client = anthropic.Anthropic(
            api_key=ANTHROPIC_API_KEY
        )
        self.call_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0

        # Token pricing per million
        self.pricing = {
            FAST_MODEL:    {"input": 0.80,  "output": 4.00},
            DEFAULT_MODEL: {"input": 3.00,  "output": 15.00},
            SMART_MODEL:   {"input": 15.00, "output": 75.00},
        }

    def route(self, task_type: str) -> str:
        """Pick the right model tier for a task type"""
        tier = ROUTING_RULES.get(task_type, "default")
        return TIERS[tier]

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost of a single call"""
        pricing = self.pricing.get(model, self.pricing[DEFAULT_MODEL])
        cost = (
            (input_tokens  / 1_000_000) * pricing["input"] +
            (output_tokens / 1_000_000) * pricing["output"]
        )
        return cost

    def call(
        self,
        prompt: str,
        task_type: str = "default",
        system: str = None,
        max_tokens: int = 1024,
        max_retries: int = 3,
        model: str = None
    ) -> str:
        """
        Make an LLM call with automatic routing,
        rate limit handling, and fallback.
        """
        # Pick model — explicit override or auto-route
        if model:
            primary_tier = "default"
            primary_model = model
        else:
            primary_tier = ROUTING_RULES.get(task_type, "default")
            primary_model = TIERS[primary_tier]

        # Get fallback chain
        fallbacks = FALLBACK_CHAIN.get(primary_tier, ["default"])
        models_to_try = [primary_model] + [
            TIERS[t] for t in fallbacks[1:]
        ]

        last_error = None

        for current_model in models_to_try:
            for attempt in range(max_retries):
                try:
                    # Build request
                    kwargs = {
                        "model": current_model,
                        "max_tokens": max_tokens,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ]
                    }
                    if system:
                        kwargs["system"] = system

                    # Make the call
                    response = self.client.messages.create(**kwargs)

                    # Track usage
                    self.call_count += 1
                    input_tokens  = response.usage.input_tokens
                    output_tokens = response.usage.output_tokens
                    self.total_tokens += input_tokens + output_tokens

                    cost = self.calculate_cost(
                        current_model, input_tokens, output_tokens
                    )
                    self.total_cost += cost

                    # Log the call
                    print(
                        f"  [Gateway] {task_type} → {current_model.split('.')[-1]} "
                        f"| {input_tokens}+{output_tokens} tokens "
                        f"| ${cost:.4f}"
                    )

                    return response.content[0].text.strip()

                except anthropic.RateLimitError as e:
                    wait = 2 ** attempt * 5  # 5s, 10s, 20s
                    print(f"  [Gateway] Rate limited — waiting {wait}s...")
                    time.sleep(wait)
                    last_error = e

                except anthropic.APIStatusError as e:
                    if e.status_code >= 500:
                        # Server error — retry
                        wait = 2 ** attempt * 2
                        print(f"  [Gateway] Server error {e.status_code} — retrying in {wait}s...")
                        time.sleep(wait)
                        last_error = e
                    else:
                        # Client error — don't retry
                        raise

                except Exception as e:
                    last_error = e
                    print(f"  [Gateway] Error with {current_model}: {e}")
                    break  # Try next model in fallback chain

        # All models and retries exhausted
        raise Exception(
            f"All models failed after retries. Last error: {last_error}"
        )

    def summary(self) -> dict:
        """Return usage summary"""
        return {
            "total_calls":  self.call_count,
            "total_tokens": self.total_tokens,
            "total_cost":   f"${self.total_cost:.4f}",
        }


# ── Singleton instance ────────────────────────────────────
# All agents share one gateway
gateway = OpenClawGateway()