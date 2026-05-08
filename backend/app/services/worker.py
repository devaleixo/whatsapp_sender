import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Iterable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import SessionLocal
from ..models import (
    AppSettings,
    Campaign,
    Contact,
    Conversation,
    Message,
    Send,
    SendQueue,
    Template,
)
from .evolution import get_client

log = logging.getLogger("worker")


def _get_window(db) -> tuple[int, int]:
    row = db.query(AppSettings).first()
    if row:
        return row.send_window_start, row.send_window_end
    return settings.bot_window_start, settings.bot_window_end


def _get_typing_delay(db) -> float:
    row = db.query(AppSettings).first()
    return float(row.typing_delay_seconds) if row else 3.0


def _allowed_weekdays(db) -> set[int]:
    row = db.query(AppSettings).first()
    raw = row.send_days if row and row.send_days else "0,1,2,3,4"
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            n = int(part)
            if 0 <= n <= 6:
                out.add(n)
    return out or {0, 1, 2, 3, 4}


def _in_send_window(db, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now()
    if now.weekday() not in _allowed_weekdays(db):
        return False
    start, end = _get_window(db)
    return start <= now.hour < end


def _today_start() -> datetime:
    return datetime.combine(datetime.now().date(), time.min)


def _format_message(template_body: str, contact: Contact) -> str:
    return (
        template_body
        .replace("{nome}", contact.name or "")
        .replace("{telefone}", contact.e164_phone or "")
        .replace("{endereco}", contact.address or "")
        .replace("{avaliacao}", contact.rating or "")
        .replace("{website}", contact.website or "")
    )


def _resolve_chain(db: Session, campaign: Campaign) -> list[int]:
    """IDs da cadeia ancestral (inclui a própria campanha) — usada para histórico."""
    ids = [campaign.id]
    cur = campaign
    seen = {campaign.id}
    while cur.parent_campaign_id and cur.parent_campaign_id not in seen:
        parent = db.get(Campaign, cur.parent_campaign_id)
        if not parent:
            break
        ids.append(parent.id)
        seen.add(parent.id)
        cur = parent
    return ids


def _root_campaign_id(db: Session, campaign: Campaign) -> int:
    chain = _resolve_chain(db, campaign)
    return chain[-1]


def _replied_phones(db: Session, e164_phones: Iterable[str]) -> set[str]:
    """Telefones (e164) que já enviaram qualquer mensagem inbound em qualquer conversation."""
    phones = list({p for p in e164_phones if p})
    if not phones:
        return set()
    rows = db.execute(
        select(Contact.e164_phone)
        .join(Conversation, Conversation.contact_id == Contact.id)
        .join(Message, Message.conversation_id == Conversation.id)
        .where(Contact.e164_phone.in_(phones), Message.direction == "in")
        .distinct()
    ).all()
    return {r[0] for r in rows}


def _replied_contact_ids(db: Session, contact_ids: Iterable[int]) -> set[int]:
    ids = list({i for i in contact_ids if i})
    if not ids:
        return set()
    rows = db.execute(
        select(Conversation.contact_id)
        .join(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.contact_id.in_(ids), Message.direction == "in")
        .distinct()
    ).all()
    return {r[0] for r in rows}


def _auto_enqueue_primary(db: Session, campaign: Campaign) -> int:
    """Auto-enfileira contatos da própria campanha que ainda não foram enviados nem estão na fila."""
    contact_ids_subq = select(Contact.id).where(Contact.campaign_id == campaign.id)
    already_sent = {
        r[0] for r in db.execute(
            select(Send.contact_id).where(
                Send.contact_id.in_(contact_ids_subq),
                Send.campaign_id == campaign.id,
                Send.status.in_(("sent", "delivered", "read")),
            )
        ).all()
    }
    already_queued = {
        r[0] for r in db.execute(
            select(SendQueue.contact_id).where(
                SendQueue.contact_id.in_(contact_ids_subq),
                SendQueue.campaign_id == campaign.id,
            )
        ).all()
    }
    pending = db.query(Contact).filter(
        Contact.campaign_id == campaign.id,
        Contact.has_whatsapp != "no",
    ).all()
    added = 0
    for ct in pending:
        if ct.id in already_sent or ct.id in already_queued:
            continue
        db.add(SendQueue(
            contact_id=ct.id,
            template_id=campaign.template_id,
            campaign_id=campaign.id,
            scheduled_for=datetime.now(),
        ))
        added += 1
    if added:
        db.commit()
        log.info("auto-enqueued %s contacts for campaign %s", added, campaign.id)
    return added


def _auto_enqueue_remarketing(db: Session, campaign: Campaign) -> int:
    """Enfileira contatos da cadeia ancestral elegíveis para follow-up.

    Critérios:
    - contato pertence à campanha-raiz da cadeia (Contact.campaign_id == root.id)
    - já recebeu Send com sucesso em qualquer campanha da cadeia
    - último Send da cadeia foi há >= remarketing_delay_hours
    - se exclude_replied: nunca respondeu (cruzando por phone ou contact id, conforme scope)
    - ainda não foi enfileirado nem enviado por ESTA campanha
    - quantidade de remarketings já recebidos pelo contato (cadeia, exceto raiz) < max_followups
    """
    chain_ids = _resolve_chain(db, campaign)
    root_id = chain_ids[-1]
    chain_excluding_root = [cid for cid in chain_ids if cid != root_id]

    delay = timedelta(hours=int(campaign.remarketing_delay_hours or 0))
    now = datetime.now()

    # Mapeia, por contato, o último Send com sucesso em qualquer campanha da cadeia.
    last_success_rows = db.execute(
        select(Send.contact_id, func.max(Send.sent_at))
        .where(
            Send.campaign_id.in_(chain_ids),
            Send.status.in_(("sent", "delivered", "read")),
            Send.sent_at.is_not(None),
        )
        .group_by(Send.contact_id)
    ).all()
    last_success: dict[int, datetime] = {cid: ts for cid, ts in last_success_rows if ts}
    if not last_success:
        return 0

    # Já enviado/agendado por ESTA campanha
    sent_here = {
        r[0] for r in db.execute(
            select(Send.contact_id).where(
                Send.campaign_id == campaign.id,
                Send.status.in_(("sent", "delivered", "read", "failed")),
            )
        ).all()
    }
    queued_here = {
        r[0] for r in db.execute(
            select(SendQueue.contact_id).where(SendQueue.campaign_id == campaign.id)
        ).all()
    }

    # Contagem de followups já recebidos por contato (em campanhas da cadeia que não são raiz)
    followups_received: dict[int, int] = {}
    if chain_excluding_root:
        rows = db.execute(
            select(Send.contact_id, func.count(Send.id))
            .where(
                Send.campaign_id.in_(chain_excluding_root),
                Send.status.in_(("sent", "delivered", "read")),
            )
            .group_by(Send.contact_id)
        ).all()
        followups_received = {cid: int(n) for cid, n in rows}

    candidate_ids = [
        cid for cid, ts in last_success.items()
        if (now - ts) >= delay
        and cid not in sent_here
        and cid not in queued_here
        and followups_received.get(cid, 0) < int(campaign.max_followups or 1)
    ]
    if not candidate_ids:
        return 0

    candidates = db.query(Contact).filter(
        Contact.id.in_(candidate_ids),
        Contact.campaign_id == root_id,
        Contact.has_whatsapp != "no",
    ).all()

    if campaign.exclude_replied:
        if (campaign.exclude_replied_scope or "phone") == "phone":
            replied = _replied_phones(db, [c.e164_phone for c in candidates])
            candidates = [c for c in candidates if c.e164_phone not in replied]
        else:
            replied = _replied_contact_ids(db, [c.id for c in candidates])
            candidates = [c for c in candidates if c.id not in replied]

    added = 0
    for ct in candidates:
        db.add(SendQueue(
            contact_id=ct.id,
            template_id=campaign.template_id,
            campaign_id=campaign.id,
            scheduled_for=now,
        ))
        added += 1
    if added:
        db.commit()
        log.info("auto-enqueued %s contacts for remarketing campaign %s", added, campaign.id)
    return added


def _auto_enqueue(db: Session, campaign: Campaign) -> int:
    if campaign.parent_campaign_id:
        return _auto_enqueue_remarketing(db, campaign)
    return _auto_enqueue_primary(db, campaign)


def _pick_next_for_campaign(db: Session, campaign: Campaign) -> Optional[SendQueue]:
    sent_today = db.query(func.count(Send.id)).filter(
        Send.campaign_id == campaign.id,
        Send.sent_at >= _today_start(),
    ).scalar() or 0
    if sent_today >= campaign.daily_limit:
        return None

    last_send = db.query(Send).filter(
        Send.campaign_id == campaign.id,
        Send.sent_at.is_not(None),
    ).order_by(Send.sent_at.desc()).first()
    if last_send and last_send.sent_at:
        elapsed = (datetime.now() - last_send.sent_at).total_seconds()
        if elapsed < campaign.delay_seconds:
            return None

    return (
        db.query(SendQueue)
        .filter(
            SendQueue.campaign_id == campaign.id,
            SendQueue.scheduled_for <= datetime.now(),
        )
        .order_by(SendQueue.priority.desc(), SendQueue.scheduled_for.asc())
        .first()
    )


def _process_item(db: Session, item: SendQueue) -> None:
    contact: Contact = db.get(Contact, item.contact_id)
    template: Template = db.get(Template, item.template_id)
    if not contact or not template:
        db.delete(item)
        db.commit()
        return

    client = get_client()

    if contact.has_whatsapp == "unknown":
        try:
            has = client.has_whatsapp(settings.instance_name, contact.e164_phone)
        except Exception as e:
            log.warning("has_whatsapp failed for %s: %s", contact.e164_phone, e)
            has = False
        contact.has_whatsapp = "yes" if has else "no"
        db.commit()

    if contact.has_whatsapp == "no":
        db.add(Send(
            contact_id=contact.id,
            template_id=template.id,
            campaign_id=item.campaign_id,
            status="failed",
            error="no_whatsapp",
            failed_at=datetime.now(),
        ))
        db.delete(item)
        db.commit()
        return

    body = _format_message(template.body, contact)
    typing = _get_typing_delay(db)
    if typing > 0:
        result = client.send_text_with_typing(settings.instance_name, contact.e164_phone, body, typing_delay=typing)
    else:
        result = client.send_text(settings.instance_name, contact.e164_phone, body)

    if result.get("error"):
        db.add(Send(
            contact_id=contact.id,
            template_id=template.id,
            campaign_id=item.campaign_id,
            status="failed",
            error=str(result.get("message", ""))[:500],
            failed_at=datetime.now(),
        ))
    else:
        msg_id = None
        key = result.get("key") or result.get("data", {}).get("key") if isinstance(result.get("data"), dict) else None
        if isinstance(key, dict):
            msg_id = key.get("id")
        db.add(Send(
            contact_id=contact.id,
            template_id=template.id,
            campaign_id=item.campaign_id,
            status="sent",
            evolution_msg_id=msg_id,
            sent_at=datetime.now(),
        ))
    db.delete(item)
    db.commit()


def tick_sync() -> int:
    """Runs one worker tick. Returns number of messages sent in this tick."""
    processed = 0
    db: Session = SessionLocal()
    try:
        if not _in_send_window(db):
            return 0
        campaigns = db.query(Campaign).filter(Campaign.status == "active").all()
        for c in campaigns:
            _auto_enqueue(db, c)
            item = _pick_next_for_campaign(db, c)
            if item is None:
                continue
            try:
                _process_item(db, item)
                processed += 1
            except Exception as e:
                log.exception("failed processing queue item %s: %s", item.id, e)
                db.rollback()
    finally:
        db.close()
    return processed


async def tick() -> None:
    sent = await asyncio.to_thread(tick_sync)
    if sent:
        log.info("worker tick: %s messages sent", sent)


def build_scheduler() -> AsyncIOScheduler:
    sched = AsyncIOScheduler()
    sched.add_job(
        tick,
        "interval",
        seconds=settings.worker_tick_seconds,
        id="sender_tick",
        max_instances=1,
        coalesce=True,
    )
    return sched
