from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_db
from ..models import InstanceState
from ..schemas import InstanceStatus
from ..services.evolution import get_client
from ..services.startup import ensure_webhook_registered


router = APIRouter(prefix="/instance", tags=["instance"])


def _upsert_state(db: Session, connected: bool, qr_seen: bool = False) -> InstanceState:
    row = db.query(InstanceState).filter_by(name=settings.instance_name).first()
    if not row:
        row = InstanceState(name=settings.instance_name)
        db.add(row)
    row.connected = connected
    row.last_checked_at = datetime.now()
    if qr_seen:
        row.last_qr_at = datetime.now()
    db.commit()
    db.refresh(row)
    return row


@router.get("/status", response_model=InstanceStatus)
def status(db: Session = Depends(get_db)):
    client = get_client()
    instances = client.list_instances()
    exists = isinstance(instances, list) and any(
        i.get("name") == settings.instance_name or i.get("instance", {}).get("instanceName") == settings.instance_name
        for i in instances
    )
    if not exists:
        client.create_instance(settings.instance_name)

    connected = client.is_connected(settings.instance_name)
    qr_b64 = None
    qr_text = None
    if not connected:
        qr = client.get_qrcode(settings.instance_name)
        qr_b64 = qr.get("base64")
        qr_text = qr.get("code")
    _upsert_state(db, connected=connected, qr_seen=bool(qr_b64 or qr_text))
    return InstanceStatus(
        name=settings.instance_name,
        connected=connected,
        qrcode_base64=qr_b64,
        qrcode_text=qr_text,
    )


@router.post("/restart")
def restart(db: Session = Depends(get_db)):
    client = get_client()
    res = client.restart_instance(settings.instance_name)
    return {"ok": not res.get("error"), "detail": res}


@router.get("/webhook")
def get_webhook_info():
    client = get_client()
    res = client.get_webhook(settings.instance_name)
    url = res.get("url") or res.get("webhook", {}).get("url") if isinstance(res, dict) else None
    expected = f"{settings.webhook_base_url.rstrip('/')}/webhook/incoming"
    return {"current_url": url, "expected_url": expected, "correct": url == expected, "raw": res}


@router.post("/webhook/register")
def register_webhook():
    """Registra/atualiza o webhook no Evolution pra mandar mensagens pro backend."""
    return ensure_webhook_registered()


@router.post("/webhook-setup")
def webhook_setup_legacy(public_url: str):
    """Legado: setar URL custom. Use /webhook/register pra auto."""
    client = get_client()
    res = client.set_webhook(settings.instance_name, public_url)
    return {"ok": not res.get("error"), "detail": res}
