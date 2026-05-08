import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import Campaign, Contact, Conversation, Message, Send, SendQueue
from ..services.bot_engine import handle_incoming
from ..services.phone import to_e164

log = logging.getLogger("webhook")

router = APIRouter(prefix="/webhook", tags=["webhook"])


def _extract_text(data: dict) -> str | None:
    msg = data.get("message") or {}
    if not msg:
        return None
    # Evolution v1.x shapes
    if isinstance(msg.get("conversation"), str):
        return msg["conversation"]
    if isinstance(msg.get("extendedTextMessage"), dict):
        return msg["extendedTextMessage"].get("text")
    if isinstance(msg.get("imageMessage"), dict):
        return msg["imageMessage"].get("caption") or "[imagem]"
    if isinstance(msg.get("videoMessage"), dict):
        return msg["videoMessage"].get("caption") or "[vídeo]"
    if isinstance(msg.get("audioMessage"), dict):
        return "[áudio]"
    if isinstance(msg.get("documentMessage"), dict):
        return msg["documentMessage"].get("caption") or "[documento]"
    if isinstance(msg.get("buttonsResponseMessage"), dict):
        return msg["buttonsResponseMessage"].get("selectedDisplayText")
    if isinstance(msg.get("listResponseMessage"), dict):
        return msg["listResponseMessage"].get("title")
    return None


def _extract_phone(jid: str | None) -> str | None:
    if not jid:
        return None
    # Formato: "5561993226767@s.whatsapp.net" ou "...@g.us" (grupos — ignoramos)
    if "@g.us" in jid:
        return None
    return jid.split("@")[0]


def _is_lid(jid: str | None) -> bool:
    return bool(jid) and "@lid" in jid


def _normalize_event(payload: dict) -> tuple[str, dict]:
    # Evolution pode usar "event" ou aninhar. Padronizamos.
    event = (payload.get("event") or payload.get("type") or "").lower().replace(".", "_")
    data = payload.get("data") or payload
    return event, data


@router.post("/incoming")
async def incoming(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    event, data = _normalize_event(payload)

    # Pode vir como MESSAGES_UPSERT / messages_upsert / MESSAGES_UPDATE etc.
    if "messages_upsert" in event or event == "messages_upsert":
        return _handle_upsert(db, data)
    if "messages_update" in event:
        return _handle_status_update(db, data)
    if "connection_update" in event:
        return {"ok": True, "noop": "connection"}

    # Webhook pode vir com chaves "messages": [ {...} ]
    messages = data.get("messages")
    if isinstance(messages, list):
        results = [_handle_upsert(db, m) for m in messages]
        return {"ok": True, "processed": len(results)}

    # Default: tenta tratar como upsert
    return _handle_upsert(db, data)


@router.post("/status")
async def status(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    _, data = _normalize_event(payload)
    return _handle_status_update(db, data)


def _handle_upsert(db: Session, data: dict) -> dict:
    key = data.get("key") or {}
    if not isinstance(key, dict):
        return {"ok": False, "reason": "no_key"}
    if key.get("fromMe"):
        return {"ok": True, "ignored": "fromMe"}

    raw_jid = key.get("remoteJid")
    phone = _extract_phone(raw_jid)
    if not phone:
        return {"ok": True, "ignored": "no_phone"}

    is_lid = _is_lid(raw_jid)
    e164 = phone if is_lid else (to_e164(phone) or phone)
    text = _extract_text(data) or ""
    push_name = data.get("pushName") or data.get("pushname")
    incoming_msg_id = key.get("id")

    contact = (
        db.query(Contact)
        .filter(Contact.e164_phone == e164)
        .order_by(Contact.created_at.desc())
        .first()
    )
    if not contact:
        display_name = push_name or ("Desconhecido (LID)" if is_lid else "Desconhecido")
        contact = Contact(
            campaign_id=None,
            name=display_name,
            phone=raw_jid or e164,
            e164_phone=e164,
            has_whatsapp="yes",
            source="inbox",
        )
        db.add(contact)
        db.flush()
        log.info("created orphan contact %s for incoming from %s", contact.id, raw_jid)

    conv = (
        db.query(Conversation).filter(Conversation.contact_id == contact.id).first()
    )
    if not conv:
        conv = Conversation(contact_id=contact.id, state="bot")
        db.add(conv)
        db.flush()

    conv.last_incoming_at = datetime.now()
    db.add(Message(
        conversation_id=conv.id,
        direction="in",
        body=text,
        from_bot=False,
        evolution_msg_id=incoming_msg_id,
        status="delivered",
    ))
    db.commit()
    db.refresh(conv)

    _drop_replied_queue(db, e164)

    try:
        handle_incoming(db, conv, text)
    except Exception as e:
        log.exception("bot handler failed: %s", e)

    return {"ok": True}


def _drop_replied_queue(db: Session, e164_phone: str) -> int:
    """Remove rows pendentes de SendQueue para esse telefone em campanhas com exclude_replied=True.

    Cobre dois casos:
    - scope='contact': exclui apenas itens do mesmo contact_id
    - scope='phone' (default): exclui itens de qualquer contact com mesmo e164_phone
    """
    contact_ids = [
        r[0] for r in db.execute(
            select(Contact.id).where(Contact.e164_phone == e164_phone)
        ).all()
    ]
    if not contact_ids:
        return 0

    items = (
        db.query(SendQueue)
        .join(Campaign, Campaign.id == SendQueue.campaign_id)
        .filter(
            Campaign.exclude_replied.is_(True),
            SendQueue.contact_id.in_(contact_ids),
        )
        .all()
    )
    if not items:
        return 0

    removed = 0
    for it in items:
        camp = db.get(Campaign, it.campaign_id) if it.campaign_id else None
        if camp and (camp.exclude_replied_scope or "phone") == "contact":
            ct = db.get(Contact, it.contact_id)
            if not ct or ct.e164_phone != e164_phone:
                continue
        db.delete(it)
        removed += 1
    if removed:
        db.commit()
        log.info("dropped %s queued sends for replied phone %s", removed, e164_phone)
    return removed


_STATUS_MAP = {
    "SERVER_ACK": "sent",
    "DELIVERY_ACK": "delivered",
    "READ": "read",
    "PLAYED": "read",
    "ERROR": "failed",
    "2": "sent",
    "3": "delivered",
    "4": "read",
    "5": "read",
    "0": "failed",
}


def _handle_status_update(db: Session, data: dict) -> dict:
    # Pode vir "keyId" ou "key": {"id": ...}
    msg_id = data.get("keyId")
    if not msg_id:
        key = data.get("key") or {}
        if isinstance(key, dict):
            msg_id = key.get("id")
    if not msg_id:
        return {"ok": False, "reason": "no_msg_id"}

    raw_status = str(data.get("status") or data.get("update", {}).get("status") or "")
    new_status = _STATUS_MAP.get(raw_status.upper()) or _STATUS_MAP.get(raw_status)
    if not new_status:
        return {"ok": True, "ignored": f"unknown_status:{raw_status}"}

    send = db.query(Send).filter(Send.evolution_msg_id == msg_id).first()
    if send:
        _apply_status(send, new_status)
        db.commit()
        return {"ok": True, "updated": "send", "status": new_status}

    message = db.query(Message).filter(Message.evolution_msg_id == msg_id).first()
    if message:
        message.status = new_status
        db.commit()
        return {"ok": True, "updated": "message", "status": new_status}

    return {"ok": True, "ignored": "msg_not_found"}


def _apply_status(send: Send, new_status: str) -> None:
    now = datetime.now()
    # Nunca regrede status
    order = {"pending": 0, "sent": 1, "delivered": 2, "read": 3, "failed": 9}
    if order.get(new_status, 0) <= order.get(send.status, 0) and new_status != "failed":
        return
    send.status = new_status
    if new_status == "delivered":
        send.delivered_at = now
    elif new_status == "read":
        send.read_at = now
        if not send.delivered_at:
            send.delivered_at = now
    elif new_status == "failed":
        send.failed_at = now
