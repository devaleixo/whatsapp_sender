import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes import (
    bot,
    campaigns,
    contacts,
    conversations,
    instance,
    queue,
    recipient_types,
    sends,
    settings as settings_route,
    templates,
    webhook,
)
from .services.startup import ensure_webhook_registered
from .services.worker import build_scheduler


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Registra webhook no Evolution sem bloquear startup se Evolution ainda não respondeu
    try:
        ensure_webhook_registered()
    except Exception as e:
        logging.warning("webhook registration on startup failed: %s", e)

    scheduler = build_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(title="WhatsApp Sender", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(recipient_types.router)
app.include_router(templates.router)
app.include_router(campaigns.router)
app.include_router(contacts.router)
app.include_router(sends.router)
app.include_router(queue.router)
app.include_router(instance.router)
app.include_router(conversations.router)
app.include_router(bot.router)
app.include_router(webhook.router)
app.include_router(settings_route.router)
