from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class ReplyDecision:
    text: Optional[str] = None
    should_handoff: bool = False
    handoff_reason: Optional[str] = None


@dataclass
class HistoryMessage:
    role: str  # "user" (cliente) | "assistant" (bot)
    content: str


class LLMProvider(Protocol):
    name: str

    def generate_reply(
        self,
        system_prompt: str,
        history: list[HistoryMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> ReplyDecision: ...
