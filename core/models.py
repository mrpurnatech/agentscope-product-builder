"""
Model factory — creates AnthropicChatModel instances for each tier.

Three tiers:
  - fast  (Haiku)  — reviews, QA, docs, validation
  - default (Sonnet) — code generation, planning, design
  - smart (Opus)   — PRD analysis, architecture, security
"""
from agentscope.model import AnthropicChatModel
from agentscope.formatter import AnthropicChatFormatter
from config.settings import (
    ANTHROPIC_API_KEY,
    FAST_MODEL,
    DEFAULT_MODEL,
    SMART_MODEL,
)

# Token pricing per million (for cost tracking)
PRICING = {
    FAST_MODEL:    {"input": 0.80,  "output": 4.00},
    DEFAULT_MODEL: {"input": 3.00,  "output": 15.00},
    SMART_MODEL:   {"input": 15.00, "output": 75.00},
}


def create_fast_model(max_tokens: int = 2048, stream: bool = False) -> AnthropicChatModel:
    """Haiku — cheap, fast. For reviews, QA, docs."""
    return AnthropicChatModel(
        model_name=FAST_MODEL,
        api_key=ANTHROPIC_API_KEY,
        max_tokens=max_tokens,
        stream=stream,
    )


def create_default_model(max_tokens: int = 4096, stream: bool = False) -> AnthropicChatModel:
    """Sonnet — balanced. For code, planning, design."""
    return AnthropicChatModel(
        model_name=DEFAULT_MODEL,
        api_key=ANTHROPIC_API_KEY,
        max_tokens=max_tokens,
        stream=stream,
    )


def create_smart_model(max_tokens: int = 8192, stream: bool = False) -> AnthropicChatModel:
    """Opus — maximum intelligence. For PRD, architecture, security."""
    return AnthropicChatModel(
        model_name=SMART_MODEL,
        api_key=ANTHROPIC_API_KEY,
        max_tokens=max_tokens,
        stream=stream,
    )


def create_formatter() -> AnthropicChatFormatter:
    """Shared formatter for all Anthropic models."""
    return AnthropicChatFormatter()


def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost of a single LLM call."""
    pricing = PRICING.get(model_name, PRICING[DEFAULT_MODEL])
    return (
        (input_tokens / 1_000_000) * pricing["input"] +
        (output_tokens / 1_000_000) * pricing["output"]
    )
