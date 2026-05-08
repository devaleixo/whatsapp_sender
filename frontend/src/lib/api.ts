const BASE = "/api";

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status}: ${text || res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  get: <T,>(p: string) => req<T>(p),
  post: <T,>(p: string, body?: unknown) =>
    req<T>(p, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  put: <T,>(p: string, body?: unknown) =>
    req<T>(p, { method: "PUT", body: body !== undefined ? JSON.stringify(body) : undefined }),
  del: <T,>(p: string) => req<T>(p, { method: "DELETE" }),
  upload: async <T,>(p: string, file: File): Promise<T> => {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${BASE}${p}`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
    return res.json();
  },
};

export type RecipientType = { id: number; slug: string; name: string };
export type Template = {
  id: number;
  recipient_type_id: number;
  name: string;
  body: string;
  variables: string[];
  active: boolean;
};
export type Campaign = {
  id: number;
  name: string;
  recipient_type_id: number;
  template_id: number;
  city: string | null;
  status: string;
  daily_limit: number;
  delay_seconds: number;
  parent_campaign_id: number | null;
  remarketing_delay_hours: number;
  exclude_replied: boolean;
  exclude_replied_scope: string;
  max_followups: number;
};
export type Contact = {
  id: number;
  campaign_id: number;
  name: string;
  phone: string;
  e164_phone: string;
  has_whatsapp: string;
  address: string | null;
  rating: string | null;
  website: string | null;
};
export type DashboardMetrics = {
  sent_today: number;
  delivered_today: number;
  read_today: number;
  failed_today: number;
  pending_queue: number;
  active_campaigns: number;
};
export type QueueItem = {
  id: number;
  contact_id: number;
  template_id: number;
  scheduled_for: string;
  priority: number;
};
export type Conversation = {
  id: number;
  contact_id: number;
  contact_name: string;
  contact_phone: string;
  state: string;
  last_snippet: string | null;
  last_incoming_at: string | null;
  unread_in_since_outgoing: number;
};
export type Message = {
  id: number;
  conversation_id: number;
  direction: "in" | "out";
  body: string;
  from_bot: boolean;
  status: string;
  created_at: string;
};
export type ConversationDetail = {
  id: number;
  contact_id: number;
  state: string;
  handoff_reason: string | null;
  last_incoming_at: string | null;
  last_outgoing_at: string | null;
  messages: Message[];
};
export type BotConfig = {
  id?: number;
  recipient_type_id: number;
  system_prompt: string;
  model: string | null;
  temperature: number;
  handoff_keywords: string[];
  active_hours_start: number;
  active_hours_end: number;
  enabled: boolean;
  provider: string;
};
export type AppSettings = {
  send_window_start: number;
  send_window_end: number;
  worker_tick_seconds: number;
  typing_delay_seconds: number;
  send_days: string;
};
export type InstanceStatus = {
  name: string;
  connected: boolean;
  qrcode_base64: string | null;
  qrcode_text: string | null;
};
