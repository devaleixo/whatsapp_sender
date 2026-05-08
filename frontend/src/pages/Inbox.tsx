import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, type Conversation, type ConversationDetail } from "../lib/api";
import { fmtTime } from "../lib/datetime";
import StatusBadge from "../components/StatusBadge";

export default function Inbox() {
  const { contactId } = useParams();
  const [list, setList] = useState<Conversation[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [draft, setDraft] = useState("");

  const loadList = () => api.get<Conversation[]>("/conversations").then(setList);

  useEffect(() => {
    loadList();
    const t = setInterval(loadList, 5000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (contactId) {
      setSelected(Number(contactId));
    }
  }, [contactId]);

  const loadDetail = async (cid: number) => {
    try {
      const d = await api.get<ConversationDetail>(`/conversations/by-contact/${cid}`);
      setDetail(d);
    } catch { setDetail(null); }
  };

  useEffect(() => {
    if (selected == null) { setDetail(null); return; }
    loadDetail(selected);
    const t = setInterval(() => loadDetail(selected), 4000);
    return () => clearInterval(t);
  }, [selected]);

  const toggleState = async (newState: "bot" | "human" | "paused") => {
    if (!detail) return;
    const updated = await api.put<ConversationDetail>(`/conversations/${detail.id}/state`, { state: newState });
    setDetail(updated);
    loadList();
  };

  const send = async () => {
    if (!detail || !draft.trim()) return;
    await api.post(`/conversations/${detail.id}/messages`, { body: draft });
    setDraft("");
    loadDetail(detail.contact_id);
  };

  const currentContact = list.find(c => c.contact_id === selected);

  return (
    <div className="flex h-[calc(100vh-3rem)] -m-6">
      <div className="w-80 border-r bg-white overflow-y-auto">
        <div className="p-3 font-bold border-b">Conversas</div>
        {list.map(c => (
          <button
            key={c.id}
            onClick={() => setSelected(c.contact_id)}
            className={`w-full text-left p-3 border-b hover:bg-slate-50 ${selected === c.contact_id ? "bg-slate-100" : ""}`}
          >
            <div className="flex justify-between items-start">
              <div className="font-medium text-sm">{c.contact_name}</div>
              <StatusBadge value={c.state} />
            </div>
            <div className="text-xs text-slate-500">{c.contact_phone}</div>
            <div className="text-xs text-slate-600 mt-1 truncate">{c.last_snippet || "-"}</div>
            {c.unread_in_since_outgoing > 0 && (
              <div className="text-xs text-emerald-600 mt-1">{c.unread_in_since_outgoing} nova(s)</div>
            )}
          </button>
        ))}
        {list.length === 0 && <div className="p-6 text-slate-500 text-center text-sm">Nenhuma conversa</div>}
      </div>

      <div className="flex-1 flex flex-col bg-slate-50">
        {!detail ? (
          <div className="flex-1 flex items-center justify-center text-slate-400">
            {selected ? "carregando..." : "Selecione uma conversa"}
          </div>
        ) : (
          <>
            <div className="p-4 border-b bg-white flex justify-between items-center">
              <div>
                <div className="font-bold">{currentContact?.contact_name}</div>
                <div className="text-xs text-slate-500">{currentContact?.contact_phone}</div>
              </div>
              <div className="flex gap-2 items-center">
                <StatusBadge value={detail.state} />
                {detail.state !== "human" && (
                  <button onClick={() => toggleState("human")} className="bg-amber-600 text-white px-3 py-1 rounded text-sm">Assumir</button>
                )}
                {detail.state === "human" && (
                  <button onClick={() => toggleState("bot")} className="bg-purple-600 text-white px-3 py-1 rounded text-sm">Devolver ao bot</button>
                )}
                <button onClick={() => toggleState("paused")} className="bg-slate-600 text-white px-3 py-1 rounded text-sm">Pausar</button>
              </div>
            </div>
            {detail.handoff_reason && (
              <div className="bg-amber-50 text-amber-800 px-4 py-2 text-sm">⚠ Handoff: {detail.handoff_reason}</div>
            )}
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {detail.messages.map(m => (
                <div key={m.id} className={`flex ${m.direction === "out" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-md px-3 py-2 rounded-lg ${
                    m.direction === "out"
                      ? m.from_bot ? "bg-purple-100" : "bg-emerald-100"
                      : "bg-white border"
                  }`}>
                    <div className="whitespace-pre-wrap text-sm">{m.body}</div>
                    <div className="text-xs text-slate-400 mt-1">
                      {fmtTime(m.created_at)} {m.from_bot && "· bot"} · {m.status}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-3 border-t bg-white flex gap-2">
              <input
                className="flex-1 border rounded px-3 py-2"
                placeholder="Mensagem manual..."
                value={draft}
                onChange={e => setDraft(e.target.value)}
                onKeyDown={e => e.key === "Enter" && send()}
              />
              <button onClick={send} className="bg-emerald-600 text-white px-4 py-2 rounded">Enviar</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
