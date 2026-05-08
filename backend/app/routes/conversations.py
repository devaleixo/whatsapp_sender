from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_db
from ..models import AppSettings, Contact, Conversation, Message
from ..schemas import (
    ConversationDetail,
    ConversationListItem,
    ConversationStateUpdate,
    ManualMessageIn,
    MessageOut,
)
from ..services.evolution import get_client


router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationListItem])
def list_conversations(db: Session = Depends(get_db)):
    convs = (
        db.query(Conversation)
        .order_by(Conversation.last_incoming_at.desc().nullslast())
        .limit(200)
        .all()
    )
    out: list[ConversationListItem] = []
    for c in convs:
        contact = db.get(Contact, c.contact_id)
        if not contact:
            continue
        last_msg = (
            db.query(Message)
            .filter(Message.conversation_id == c.id)
            .order_by(Message.created_at.desc())
            .first()
        )
        snippet = (last_msg.body[:80] if last_msg else None)
        unread = 0
        if c.last_outgoing_at:
            unread = db.query(Message).filter(
                Message.conversation_id == c.id,
                Message.direction == "in",
                Message.created_at > c.last_outgoing_at,
            ).count()
        else:
            unread = db.query(Message).filter(
                Message.conversation_id == c.id,
                Message.direction == "in",
            ).count()
        out.append(ConversationListItem(
            id=c.id,
            contact_id=contact.id,
            contact_name=contact.name,
            contact_phone=contact.phone,
            state=c.state,
            last_snippet=snippet,
            last_incoming_at=c.last_incoming_at,
            unread_in_since_outgoing=unread,
        ))
    return out


@router.get("/by-contact/{contact_id}", response_model=ConversationDetail)
def get_by_contact(contact_id: int, db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.contact_id == contact_id).first()
    if not conv:
        raise HTTPException(404, "no conversation")
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return ConversationDetail(
        id=conv.id,
        contact_id=conv.contact_id,
        state=conv.state,
        handoff_reason=conv.handoff_reason,
        last_incoming_at=conv.last_incoming_at,
        last_outgoing_at=conv.last_outgoing_at,
        messages=[MessageOut.model_validate(m) for m in msgs],
    )


@router.put("/{conversation_id}/state", response_model=ConversationDetail)
def update_state(conversation_id: int, payload: ConversationStateUpdate, db: Session = Depends(get_db)):
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(404)
    if payload.state not in ("bot", "human", "paused"):
        raise HTTPException(400, "invalid state")
    conv.state = payload.state
    if payload.state != "human":
        conv.handoff_reason = None
    db.commit()
    db.refresh(conv)
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return ConversationDetail(
        id=conv.id,
        contact_id=conv.contact_id,
        state=conv.state,
        handoff_reason=conv.handoff_reason,
        last_incoming_at=conv.last_incoming_at,
        last_outgoing_at=conv.last_outgoing_at,
        messages=[MessageOut.model_validate(m) for m in msgs],
    )


@router.post("/{conversation_id}/messages", response_model=MessageOut)
def send_manual(conversation_id: int, payload: ManualMessageIn, db: Session = Depends(get_db)):
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(404)
    contact = db.get(Contact, conv.contact_id)
    if not contact:
        raise HTTPException(404, "contact gone")

    client = get_client()
    app_cfg = db.query(AppSettings).first()
    typing = float(app_cfg.typing_delay_seconds) if app_cfg else 0.0
    if typing > 0:
        result = client.send_text_with_typing(settings.instance_name, contact.e164_phone, payload.body, typing_delay=typing)
    else:
        result = client.send_text(settings.instance_name, contact.e164_phone, payload.body)
    msg_id = None
    key = result.get("key") or (result.get("data", {}) or {}).get("key")
    if isinstance(key, dict):
        msg_id = key.get("id")

    m = Message(
        conversation_id=conv.id,
        direction="out",
        body=payload.body,
        from_bot=False,
        evolution_msg_id=msg_id,
        status="sent" if not result.get("error") else "failed",
    )
    db.add(m)
    conv.last_outgoing_at = datetime.now()
    db.commit()
    db.refresh(m)
    return m
