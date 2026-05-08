from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import (
    Campaign,
    Contact,
    Conversation,
    Message,
    RecipientType,
    Send,
    SendQueue,
    Template,
)
from ..schemas import CampaignIn, CampaignOut, CampaignUpdate, RemarketingIn


router = APIRouter(prefix="/campaigns", tags=["campaigns"])


def _resolve_chain_ids(db: Session, campaign: Campaign) -> list[int]:
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


@router.get("", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db)):
    return db.query(Campaign).order_by(Campaign.created_at.desc()).all()


@router.post("", response_model=CampaignOut, status_code=201)
def create_campaign(payload: CampaignIn, db: Session = Depends(get_db)):
    if not db.get(RecipientType, payload.recipient_type_id):
        raise HTTPException(400, "recipient_type_id not found")
    tpl = db.get(Template, payload.template_id)
    if not tpl or tpl.recipient_type_id != payload.recipient_type_id:
        raise HTTPException(400, "template does not match recipient type")
    if payload.parent_campaign_id is not None:
        parent = db.get(Campaign, payload.parent_campaign_id)
        if not parent:
            raise HTTPException(400, "parent_campaign_id not found")
        if parent.recipient_type_id != payload.recipient_type_id:
            raise HTTPException(400, "parent recipient type mismatch")
    c = Campaign(**payload.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    c = db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(404)
    return c


@router.put("/{campaign_id}", response_model=CampaignOut)
def update_campaign(campaign_id: int, payload: CampaignUpdate, db: Session = Depends(get_db)):
    c = db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(404)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    c = db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(404)
    db.delete(c)
    db.commit()


@router.post("/{campaign_id}/enqueue")
def enqueue_pending(campaign_id: int, db: Session = Depends(get_db)):
    c = db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(404)

    contact_ids_subq = select(Contact.id).where(Contact.campaign_id == campaign_id)
    already_sent = set(
        r[0] for r in db.execute(
            select(Send.contact_id).where(
                Send.contact_id.in_(contact_ids_subq),
                Send.campaign_id == campaign_id,
                Send.status.in_(("sent", "delivered", "read")),
            )
        ).all()
    )
    already_queued = set(
        r[0] for r in db.execute(
            select(SendQueue.contact_id).where(
                SendQueue.contact_id.in_(contact_ids_subq),
                SendQueue.campaign_id == campaign_id,
            )
        ).all()
    )

    contacts = db.query(Contact).filter(
        Contact.campaign_id == campaign_id,
        Contact.has_whatsapp != "no",
    ).all()

    enqueued = 0
    for ct in contacts:
        if ct.id in already_sent or ct.id in already_queued:
            continue
        db.add(SendQueue(
            contact_id=ct.id,
            template_id=c.template_id,
            campaign_id=c.id,
            scheduled_for=datetime.now(),
        ))
        enqueued += 1
    db.commit()
    return {"enqueued": enqueued, "skipped": len(contacts) - enqueued}


@router.get("/{campaign_id}/stats")
def campaign_stats(campaign_id: int, db: Session = Depends(get_db)):
    c = db.get(Campaign, campaign_id)
    if not c:
        raise HTTPException(404)

    sent = db.query(func.count(Send.id)).filter(
        Send.campaign_id == campaign_id,
        Send.status.in_(("sent", "delivered", "read")),
    ).scalar() or 0
    failed = db.query(func.count(Send.id)).filter(
        Send.campaign_id == campaign_id,
        Send.status == "failed",
    ).scalar() or 0
    queued = db.query(func.count(SendQueue.id)).filter(
        SendQueue.campaign_id == campaign_id
    ).scalar() or 0

    base: dict = {"sent": sent, "failed": failed, "queued": queued}

    if c.parent_campaign_id is None:
        total = db.query(func.count(Contact.id)).filter(
            Contact.campaign_id == campaign_id
        ).scalar() or 0
        base["total_contacts"] = total
        base["is_remarketing"] = False
        return base

    # Remarketing: contagem de elegíveis na cadeia ancestral.
    chain_ids = _resolve_chain_ids(db, c)
    root_id = chain_ids[-1]
    total_in_root = db.query(func.count(Contact.id)).filter(
        Contact.campaign_id == root_id
    ).scalar() or 0

    delay_cutoff = datetime.now() - timedelta(hours=int(c.remarketing_delay_hours or 0))

    last_success = dict(db.execute(
        select(Send.contact_id, func.max(Send.sent_at))
        .where(
            Send.campaign_id.in_(chain_ids),
            Send.status.in_(("sent", "delivered", "read")),
            Send.sent_at.is_not(None),
        )
        .group_by(Send.contact_id)
    ).all())

    eligible_ids = {cid for cid, ts in last_success.items() if ts and ts <= delay_cutoff}

    replied_excluded = 0
    if c.exclude_replied and eligible_ids:
        if (c.exclude_replied_scope or "phone") == "phone":
            phones = [
                r[0] for r in db.execute(
                    select(Contact.e164_phone).where(Contact.id.in_(eligible_ids))
                ).all()
            ]
            replied_phones = {
                r[0] for r in db.execute(
                    select(Contact.e164_phone)
                    .join(Conversation, Conversation.contact_id == Contact.id)
                    .join(Message, Message.conversation_id == Conversation.id)
                    .where(Contact.e164_phone.in_(phones), Message.direction == "in")
                    .distinct()
                ).all()
            }
            replied_excluded = sum(1 for p in phones if p in replied_phones)
            id_phone = dict(db.execute(
                select(Contact.id, Contact.e164_phone).where(Contact.id.in_(eligible_ids))
            ).all())
            eligible_ids = {cid for cid in eligible_ids if id_phone.get(cid) not in replied_phones}
        else:
            replied_ids = {
                r[0] for r in db.execute(
                    select(Conversation.contact_id)
                    .join(Message, Message.conversation_id == Conversation.id)
                    .where(Conversation.contact_id.in_(eligible_ids), Message.direction == "in")
                    .distinct()
                ).all()
            }
            replied_excluded = len(replied_ids)
            eligible_ids -= replied_ids

    base["total_contacts"] = total_in_root
    base["is_remarketing"] = True
    base["chain_ids"] = chain_ids
    base["eligible_for_followup"] = len(eligible_ids)
    base["replied_excluded"] = replied_excluded
    return base


@router.post("/{campaign_id}/remarketing", response_model=CampaignOut, status_code=201)
def create_remarketing(campaign_id: int, payload: RemarketingIn, db: Session = Depends(get_db)):
    parent = db.get(Campaign, campaign_id)
    if not parent:
        raise HTTPException(404, "parent campaign not found")

    tpl = db.get(Template, payload.template_id)
    if not tpl or tpl.recipient_type_id != parent.recipient_type_id:
        raise HTTPException(400, "template does not match parent recipient type")

    name = payload.name or f"{parent.name} — follow-up"
    c = Campaign(
        name=name,
        recipient_type_id=parent.recipient_type_id,
        template_id=payload.template_id,
        city=parent.city,
        status="draft",
        daily_limit=payload.daily_limit,
        delay_seconds=payload.delay_seconds,
        parent_campaign_id=parent.id,
        remarketing_delay_hours=payload.remarketing_delay_hours,
        exclude_replied=payload.exclude_replied,
        exclude_replied_scope=payload.exclude_replied_scope,
        max_followups=payload.max_followups,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c
