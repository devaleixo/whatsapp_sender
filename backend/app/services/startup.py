import logging

from ..config import settings
from .evolution import get_client

log = logging.getLogger("startup")


def ensure_webhook_registered() -> dict:
    """Garante que a instância existe e que o webhook aponta pro backend."""
    client = get_client()
    target_url = f"{settings.webhook_base_url.rstrip('/')}/webhook/incoming"

    # 1. Cria instância se não existir
    instances = client.list_instances()
    exists = False
    if isinstance(instances, list):
        for i in instances:
            name = i.get("name") or i.get("instance", {}).get("instanceName")
            if name == settings.instance_name:
                exists = True
                break
    if not exists:
        r = client.create_instance(settings.instance_name)
        msg = str(r.get("message", ""))
        if r.get("error") and "already" not in msg.lower():
            log.warning("create_instance failed: %s", msg)

    # 2. Verifica webhook atual
    current = client.get_webhook(settings.instance_name)
    current_url = (
        current.get("url")
        or current.get("webhook", {}).get("url")
        if isinstance(current, dict) else None
    )

    if current_url == target_url:
        log.info("webhook already set to %s", target_url)
        return {"status": "ok", "url": target_url, "changed": False}

    # 3. Seta webhook
    r = client.set_webhook(settings.instance_name, target_url)
    if r.get("error"):
        log.warning("set_webhook failed: %s", r.get("message"))
        return {"status": "error", "detail": r, "url": target_url}

    log.info("webhook registered: %s", target_url)
    return {"status": "ok", "url": target_url, "changed": True}
