from typing import Optional

from .base import HistoryMessage, ReplyDecision


class StubProvider:
    """Provider default: não gera resposta. Bot fica mudo até o usuário
    conectar um provider real (Claude, OpenAI, Ollama)."""

    name = "stub"

    def generate_reply(
        self,
        system_prompt: str,
        history: list[HistoryMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
    ) -> ReplyDecision:
        return ReplyDecision(text=None, should_handoff=False)
