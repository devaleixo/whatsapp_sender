from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Recipient types

class RecipientTypeIn(BaseModel):
    slug: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)


class RecipientTypeOut(ORMBase):
    id: int
    slug: str
    name: str
    created_at: datetime


# Templates

class TemplateIn(BaseModel):
    recipient_type_id: int
    name: str
    body: str
    variables: list[str] = []
    active: bool = True


class TemplateOut(ORMBase):
    id: int
    recipient_type_id: int
    name: str
    body: str
    variables: list
    active: bool
    created_at: datetime


# Campaigns

class CampaignIn(BaseModel):
    name: str
    recipient_type_id: int
    template_id: int
    city: Optional[str] = None
    daily_limit: int = 20
    delay_seconds: int = 60
    parent_campaign_id: Optional[int] = None
    remarketing_delay_hours: int = 48
    exclude_replied: bool = True
    exclude_replied_scope: str = "phone"
    max_followups: int = 1


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    template_id: Optional[int] = None
    city: Optional[str] = None
    status: Optional[str] = None
    daily_limit: Optional[int] = None
    delay_seconds: Optional[int] = None
    remarketing_delay_hours: Optional[int] = None
    exclude_replied: Optional[bool] = None
    exclude_replied_scope: Optional[str] = None
    max_followups: Optional[int] = None


class CampaignOut(ORMBase):
    id: int
    name: str
    recipient_type_id: int
    template_id: int
    city: Optional[str]
    status: str
    daily_limit: int
    delay_seconds: int
    parent_campaign_id: Optional[int]
    remarketing_delay_hours: int
    exclude_replied: bool
    exclude_replied_scope: str
    max_followups: int
    created_at: datetime


class RemarketingIn(BaseModel):
    name: Optional[str] = None
    template_id: int
    daily_limit: int = 20
    delay_seconds: int = 60
    remarketing_delay_hours: int = 48
    exclude_replied: bool = True
    exclude_replied_scope: str = "phone"
    max_followups: int = 1


# Contacts

class ContactIn(BaseModel):
    name: str
    phone: str
    address: Optional[str] = None
    neighborhood: Optional[str] = None
    rating: Optional[str] = None
    rating_count: Optional[str] = None
    website: Optional[str] = None
    business_type: Optional[str] = None
    business_status: Optional[str] = None
    place_id: Optional[str] = None
    source: Optional[str] = None


class ContactOut(ORMBase):
    id: int
    campaign_id: Optional[int]
    name: str
    phone: str
    e164_phone: str
    address: Optional[str]
    neighborhood: Optional[str]
    rating: Optional[str]
    rating_count: Optional[str]
    website: Optional[str]
    business_type: Optional[str]
    business_status: Optional[str]
    place_id: Optional[str]
    has_whatsapp: str
    source: Optional[str]
    created_at: datetime


class ImportResult(BaseModel):
    imported: int
    skipped: int
    invalid: int


# Sends / metrics

class SendOut(ORMBase):
    id: int
    contact_id: int
    template_id: int
    campaign_id: Optional[int]
    status: str
    evolution_msg_id: Optional[str]
    error: Optional[str]
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    read_at: Optional[datetime]
    failed_at: Optional[datetime]


class DashboardMetrics(BaseModel):
    sent_today: int
    delivered_today: int
    read_today: int
    failed_today: int
    pending_queue: int
    active_campaigns: int


# Queue

class QueueItemOut(ORMBase):
    id: int
    contact_id: int
    template_id: int
    campaign_id: Optional[int]
    scheduled_for: datetime
    priority: int


# Conversations

class MessageOut(ORMBase):
    id: int
    conversation_id: int
    direction: str
    body: str
    from_bot: bool
    status: str
    created_at: datetime


class ConversationListItem(BaseModel):
    id: int
    contact_id: int
    contact_name: str
    contact_phone: str
    state: str
    last_snippet: Optional[str]
    last_incoming_at: Optional[datetime]
    unread_in_since_outgoing: int


class ConversationDetail(ORMBase):
    id: int
    contact_id: int
    state: str
    handoff_reason: Optional[str]
    last_incoming_at: Optional[datetime]
    last_outgoing_at: Optional[datetime]
    messages: list[MessageOut]


class ConversationStateUpdate(BaseModel):
    state: str  # bot|human|paused


class ManualMessageIn(BaseModel):
    body: str


# Bot config

class BotConfigIn(BaseModel):
    recipient_type_id: int
    system_prompt: str = ""
    model: Optional[str] = None
    temperature: float = 0.7
    handoff_keywords: list[str] = []
    active_hours_start: int = 8
    active_hours_end: int = 18
    enabled: bool = False
    provider: str = "stub"


class BotConfigOut(ORMBase):
    id: int
    recipient_type_id: int
    system_prompt: str
    model: Optional[str]
    temperature: float
    handoff_keywords: list
    active_hours_start: int
    active_hours_end: int
    enabled: bool
    provider: str


# App settings

class AppSettingsOut(BaseModel):
    send_window_start: int
    send_window_end: int
    worker_tick_seconds: int
    typing_delay_seconds: int
    send_days: str


class AppSettingsIn(BaseModel):
    send_window_start: int = Field(ge=0, le=23)
    send_window_end: int = Field(ge=1, le=24)
    worker_tick_seconds: int = Field(ge=10, le=3600)
    typing_delay_seconds: int = Field(ge=0, le=30)
    send_days: str = Field(default="0,1,2,3,4", pattern=r"^[0-6](,[0-6])*$|^$")


# Instance

class InstanceStatus(BaseModel):
    name: str
    connected: bool
    qrcode_base64: Optional[str] = None
    qrcode_text: Optional[str] = None
