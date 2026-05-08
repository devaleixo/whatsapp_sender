import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..config import settings
from ..models import AppSettings, BotConfig, Contact, Conversation, Message
from .evolution import get_client
from .llm import get_provider
from .llm.base import HistoryMessage
from .notifier import send_handoff_alert

log = logging.getLogger("bot_engine")

HISTORY_LIMIT = 20


def _in_bot_window(cfg: BotConfig, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now()
    return cfg.active_hours_start <= now.hour < cfg.active_hours_end


def _build_history(db: Session, conversation: Conversation) -> list[HistoryMessage]:
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    msgs = list(reversed(msgs))
    return [
        HistoryMessage(role="user" if m.direction == "in" else "assistant", content=m.body)
        for m in msgs
    ]


def _keyword_handoff(text: str, keywords: list[str]) -> Optional[str]:
    if not keywords or not text:
        return None
    lower = text.lower()
    for kw in keywords:
        if kw and kw.lower() in lower:
            return f"keyword: {kw}"
    return None


def handle_incoming(db: Session, conversation: Conversation, incoming_text: str) -> None:
    """Chamado após gravar a mensagem de entrada. Decide se bot responde."""
    if conversation.state != "bot":
        return

    contact: Contact = db.get(Contact, conversation.contact_id)
    if not contact:
        return

    campaign = contact.campaign
    cfg: Optional[BotConfig] = (
        db.query(BotConfig)
        .filter(BotConfig.recipient_type_id == campaign.recipient_type_id)
        .first()
    ) if campaign else None

    if not cfg or not cfg.enabled:
        return
    if not _in_bot_window(cfg):
        return

    # Handoff por keyword antes de chamar LLM
    reason = _keyword_handoff(incoming_text, cfg.handoff_keywords or [])
    if reason:
        _do_handoff(db, conversation, contact, reason)
        return

    provider = get_provider(cfg.provider)
    history = _build_history(db, conversation)
    try:
        decision = provider.generate_reply(
            system_prompt=cfg.system_prompt,
            history=history,
            model=cfg.model,
            temperature=cfg.temperature,
        )
    except Exception as e:
        log.exception("LLM provider failed: %s", e)
        return

    if decision.should_handoff:
        _do_handoff(db, conversation, contact, decision.handoff_reason or "LLM escalated")
        return

    if not decision.text:
        return

    client = get_client()
    app_cfg = db.query(AppSettings).first()
    typing = float(app_cfg.typing_delay_seconds) if app_cfg else 3.0
    if typing > 0:
        result = client.send_text_with_typing(settings.instance_name, contact.e164_phone, decision.text, typing_delay=typing)
    else:
        result = client.send_text(settings.instance_name, contact.e164_phone, decision.text)
    msg_id = None
    key = result.get("key") or (result.get("data", {}) or {}).get("key")
    if isinstance(key, dict):
        msg_id = key.get("id")
    db.add(Message(
        conversation_id=conversation.id,
        direction="out",
        body=decision.text,
        from_bot=True,
        evolution_msg_id=msg_id,
        status="sent" if not result.get("error") else "failed",
    ))
    conversation.last_outgoing_at = datetime.now()
    db.commit()


def _do_handoff(db: Session, conversation: Conversation, contact: Contact, reason: str) -> None:
    conversation.state = "human"
    conversation.handoff_reason = reason
    db.commit()
    send_handoff_alert(
        contact_name=contact.name,
        contact_phone=contact.phone,
        contact_id=contact.id,
        reason=reason,
    )
