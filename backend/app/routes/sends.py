from datetime import datetime, time

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import Campaign, Send, SendQueue
from ..schemas import DashboardMetrics, SendOut


router = APIRouter(tags=["sends"])


def _today_start() -> datetime:
    return datetime.combine(datetime.now().date(), time.min)


@router.get("/metrics", response_model=DashboardMetrics)
def metrics(db: Session = Depends(get_db)):
    start = _today_start()
    sent = db.query(func.count(Send.id)).filter(Send.sent_at >= start).scalar() or 0
    delivered = db.query(func.count(Send.id)).filter(Send.delivered_at >= start).scalar() or 0
    read = db.query(func.count(Send.id)).filter(Send.read_at >= start).scalar() or 0
    failed = db.query(func.count(Send.id)).filter(Send.failed_at >= start).scalar() or 0
    queued = db.query(func.count(SendQueue.id)).scalar() or 0
    active = db.query(func.count(Campaign.id)).filter(Campaign.status == "active").scalar() or 0
    return DashboardMetrics(
        sent_today=sent,
        delivered_today=delivered,
        read_today=read,
        failed_today=failed,
        pending_queue=queued,
        active_campaigns=active,
    )


@router.get("/sends", response_model=list[SendOut])
def list_sends(limit: int = 50, status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Send)
    if status:
        q = q.filter(Send.status == status)
    return q.order_by(Send.created_at.desc()).limit(limit).all()


@router.post("/sends/{send_id}/retry")
def retry_send(send_id: int, db: Session = Depends(get_db)):
    s = db.get(Send, send_id)
    if not s or s.status != "failed":
        return {"ok": False}
    db.add(SendQueue(
        contact_id=s.contact_id,
        template_id=s.template_id,
        campaign_id=s.campaign_id,
        scheduled_for=datetime.now(),
    ))
    db.delete(s)
    db.commit()
    return {"ok": True}
