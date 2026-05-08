import logging

from ..config import settings
from .evolution import get_client

log = logging.getLogger("notifier")


def send_handoff_alert(contact_name: str, contact_phone: str, contact_id: int, reason: str) -> None:
    if not settings.alert_phone:
        return
    msg = (
        "🔥 Lead quente\n"
        f"Nome: {contact_name}\n"
        f"Telefone: {contact_phone}\n"
        f"Motivo: {reason}\n"
        f"Inbox: {settings.frontend_url}/inbox/{contact_id}"
    )
    try:
        client = get_client()
        client.send_text(settings.instance_name, settings.alert_phone, msg)
    except Exception as e:
        log.warning("failed to send handoff alert: %s", e)
