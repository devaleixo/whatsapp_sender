from .base import LLMProvider, ReplyDecision
from .stub import StubProvider


def get_provider(name: str) -> LLMProvider:
    name = (name or "stub").lower()
    if name == "stub":
        return StubProvider()
    # Futuro: claude, openai, ollama
    return StubProvider()


__all__ = ["LLMProvider", "ReplyDecision", "get_provider"]
