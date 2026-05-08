from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    # Nome histórico; retorna horário local do container (TZ env var, default BRT).
    return datetime.now()


class RecipientType(Base):
    __tablename__ = "recipient_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    templates: Mapped[list["Template"]] = relationship(back_populates="recipient_type", cascade="all, delete-orphan")
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="recipient_type")
    bot_config: Mapped[Optional["BotConfig"]] = relationship(back_populates="recipient_type", uselist=False, cascade="all, delete-orphan")


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient_type_id: Mapped[int] = mapped_column(ForeignKey("recipient_types.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    recipient_type: Mapped["RecipientType"] = relationship(back_populates="templates")
    campaigns: Mapped[list["Campaign"]] = relationship(back_populates="template")


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    recipient_type_id: Mapped[int] = mapped_column(ForeignKey("recipient_types.id"), nullable=False)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)  # draft|active|paused|done
    daily_limit: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    delay_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    parent_campaign_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True
    )
    remarketing_delay_hours: Mapped[int] = mapped_column(Integer, default=48, nullable=False)
    exclude_replied: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    exclude_replied_scope: Mapped[str] = mapped_column(String(16), default="phone", nullable=False)  # phone|contact
    max_followups: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    recipient_type: Mapped["RecipientType"] = relationship(back_populates="campaigns")
    template: Mapped["Template"] = relationship(back_populates="campaigns")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    parent: Mapped[Optional["Campaign"]] = relationship(
        "Campaign", remote_side="Campaign.id", back_populates="children"
    )
    children: Mapped[list["Campaign"]] = relationship(
        "Campaign", back_populates="parent"
    )


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (UniqueConstraint("campaign_id", "e164_phone", name="uq_contact_campaign_phone"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # nullable: contatos órfãos vêm de mensagens de entrada de números desconhecidos
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    phone: Mapped[str] = mapped_column(String(64), nullable=False)
    e164_phone: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    address: Mapped[Optional[str]] = mapped_column(Text)
    rating: Mapped[Optional[str]] = mapped_column(String(16))
    website: Mapped[Optional[str]] = mapped_column(String(512))
    has_whatsapp: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)  # unknown|yes|no
    source: Mapped[Optional[str]] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    campaign: Mapped["Campaign"] = relationship(back_populates="contacts")
    sends: Mapped[list["Send"]] = relationship(back_populates="contact", cascade="all, delete-orphan")
    conversation: Mapped[Optional["Conversation"]] = relationship(back_populates="contact", uselist=False, cascade="all, delete-orphan")


class SendQueue(Base):
    __tablename__ = "send_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False)
    campaign_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True, index=True
    )
    scheduled_for: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Send(Base):
    __tablename__ = "sends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False)
    campaign_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)
    # pending|sent|delivered|read|failed
    evolution_msg_id: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    error: Mapped[Optional[str]] = mapped_column(Text)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    contact: Mapped["Contact"] = relationship(back_populates="sends")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("contacts.id", ondelete="CASCADE"), unique=True, nullable=False)
    state: Mapped[str] = mapped_column(String(16), default="bot", nullable=False)  # bot|human|paused
    handoff_reason: Mapped[Optional[str]] = mapped_column(Text)
    last_incoming_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_outgoing_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    contact: Mapped["Contact"] = relationship(back_populates="conversation")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(4), nullable=False)  # in|out
    body: Mapped[str] = mapped_column(Text, nullable=False)
    from_bot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evolution_msg_id: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(16), default="sent", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class BotConfig(Base):
    __tablename__ = "bot_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipient_type_id: Mapped[int] = mapped_column(ForeignKey("recipient_types.id", ondelete="CASCADE"), unique=True, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(64))
    temperature: Mapped[float] = mapped_column(default=0.7, nullable=False)
    handoff_keywords: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    active_hours_start: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    active_hours_end: Mapped[int] = mapped_column(Integer, default=18, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="stub", nullable=False)  # stub|claude|openai|ollama
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    recipient_type: Mapped["RecipientType"] = relationship(back_populates="bot_config")


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    send_window_start: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    send_window_end: Mapped[int] = mapped_column(Integer, default=18, nullable=False)
    worker_tick_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    typing_delay_seconds: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    # CSV de weekdays (Mon=0..Sun=6) em que o worker pode enviar. Default: dias úteis.
    send_days: Mapped[str] = mapped_column(String(32), default="0,1,2,3,4", nullable=False)


class InstanceState(Base):
    __tablename__ = "instance_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_qr_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
