"""
ProductAgent — base class for all product builder agents.

Extends AgentBase with:
  - Direct LLM call helpers (call_llm, call_llm_json)
  - Build context management via Msg.metadata
  - Cost tracking integration
"""
import json
from typing import Any

from agentscope.agent import AgentBase
from agentscope.message import Msg
from agentscope.model import AnthropicChatModel

from core.cost_tracker import cost_tracker


def parse_json(text: str) -> dict:
    """Parse JSON from LLM response, stripping markdown fences."""
    raw = text.strip()
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else parts[0]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


class ProductAgent(AgentBase):
    """
    Base class for all product builder agents.

    Each agent:
    - Has a model (Haiku/Sonnet/Opus)
    - Has a system prompt defining its role
    - Communicates via Msg objects
    - Stores structured output in Msg.metadata["build_context"]
    """

    def __init__(
        self,
        name: str,
        model: AnthropicChatModel,
        sys_prompt: str,
    ) -> None:
        super().__init__()
        self.name = name
        self.model = model
        self.sys_prompt = sys_prompt

    async def call_llm(self, prompt: str, **kwargs: Any) -> str:
        """Call the LLM with system prompt + user prompt. Returns raw text."""
        messages = [
            {"role": "system", "content": self.sys_prompt},
            {"role": "user", "content": prompt},
        ]
        response = await self.model(messages=messages, **kwargs)
        # Track cost
        if hasattr(response, "usage") and response.usage:
            cost_tracker.record(
                model=self.model.model_name,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
        return response.text

    async def call_llm_json(self, prompt: str, **kwargs: Any) -> dict:
        """Call LLM and parse JSON response."""
        text = await self.call_llm(prompt, **kwargs)
        return parse_json(text)

    def get_build_context(self, msg: Msg) -> dict:
        """Extract the accumulated build context from a message."""
        if msg is None:
            return {}
        metadata = msg.metadata or {}
        return metadata.get("build_context", {})

    def make_reply(self, content: str, build_context: dict) -> Msg:
        """Create a reply Msg with updated build context in metadata."""
        return Msg(
            name=self.name,
            content=content,
            role="assistant",
            metadata={"build_context": build_context},
        )

    async def observe(self, msg: Msg | list[Msg] | None) -> None:
        """Default observe — no-op. Override if agent needs to track messages."""
        pass

    async def reply(self, msg: Msg | None = None) -> Msg:
        """Override in subclasses."""
        raise NotImplementedError
