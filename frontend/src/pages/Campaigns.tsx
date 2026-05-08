import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Campaign, type RecipientType, type Template } from "../lib/api";
import StatusBadge from "../components/StatusBadge";

type EditKey = "daily_limit" | "delay_seconds";

export default function Campaigns() {
  const [types, setTypes] = useState<RecipientType[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [form, setForm] = useState({
    name: "", recipient_type_id: 0, template_id: 0, city: "",
    daily_limit: 20, delay_seconds: 60,
  });
  const [editing, setEditing] = useState<{ id: number; field: EditKey } | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);

  const load = async () => {
    setTypes(await api.get<RecipientType[]>("/recipient-types"));
    setTemplates(await api.get<Template[]>("/templates"));
    setCampaigns(await api.get<Campaign[]>("/campaigns"));
  };
  useEffect(() => { load(); }, []);

  const filteredTemplates = templates.filter(t => t.recipient_type_id === form.recipient_type_id);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    try {
      await api.post("/campaigns", form);
      setForm({ name: "", recipient_type_id: 0, template_id: 0, city: "", daily_limit: 20, delay_seconds: 60 });
      load();
    } catch (e: any) { setErr(String(e)); }
  };

  const updateStatus = async (id: number, status: string) => {
    await api.put(`/campaigns/${id}`, { status });
    load();
  };

  const remove = async (id: number) => {
    if (!confirm("Excluir campanha e todos os contatos?")) return;
    await api.del(`/campaigns/${id}`);
    load();
  };

  const startEdit = (c: Campaign, field: EditKey) => {
    setEditing({ id: c.id, field });
    setEditValue(String(c[field]));
  };

  const cancelEdit = () => { setEditing(null); setEditValue(""); };

  const saveEdit = async () => {
    if (!editing) return;
    const num = Number(editValue);
    if (!Number.isFinite(num) || num < 1) { cancelEdit(); return; }
    try {
      await api.put(`/campaigns/${editing.id}`, { [editing.field]: num });
      cancelEdit();
      load();
    } catch (e: any) { setErr(String(e)); cancelEdit(); }
  };

  const renderEditable = (c: Campaign, field: EditKey) => {
    const isEditing = editing?.id === c.id && editing.field === field;
    if (isEditing) {
      return (
        <input
          autoFocus
          type="number"
          min={1}
          className="w-20 border rounded px-2 py-1 text-sm"
          value={editValue}
          onChange={e => setEditValue(e.target.value)}
          onBlur={saveEdit}
          onKeyDown={e => {
            if (e.key === "Enter") saveEdit();
            if (e.key === "Escape") cancelEdit();
          }}
        />
      );
    }
    return (
      <button
        onClick={() => startEdit(c, field)}
        className="hover:bg-slate-100 px-2 py-1 rounded"
        title="Clique para editar"
      >
        {c[field]}
      </button>
    );
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Campanhas</h1>
      <form onSubmit={create} className="bg-white p-4 rounded shadow mb-6 grid grid-cols-3 gap-3">
        <input className="border rounded px-3 py-2" placeholder="Nome" value={form.name}
               onChange={e => setForm({ ...form, name: e.target.value })} required />
        <select className="border rounded px-3 py-2" value={form.recipient_type_id}
                onChange={e => setForm({ ...form, recipient_type_id: Number(e.target.value), template_id: 0 })} required>
          <option value={0}>Tipo...</option>
          {types.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <select className="border rounded px-3 py-2" value={form.template_id}
                onChange={e => setForm({ ...form, template_id: Number(e.target.value) })} required>
          <option value={0}>Template...</option>
          {filteredTemplates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
        <input className="border rounded px-3 py-2" placeholder="Cidade" value={form.city}
               onChange={e => setForm({ ...form, city: e.target.value })} />
        <input type="number" className="border rounded px-3 py-2" placeholder="Limite diário" value={form.daily_limit}
               onChange={e => setForm({ ...form, daily_limit: Number(e.target.value) })} />
        <input type="number" className="border rounded px-3 py-2" placeholder="Delay (s)" value={form.delay_seconds}
               onChange={e => setForm({ ...form, delay_seconds: Number(e.target.value) })} />
        <button className="col-span-3 bg-emerald-600 text-white px-4 py-2 rounded">Criar Campanha</button>
      </form>
      {err && <div className="text-red-600 mb-4">{err}</div>}
      <table className="w-full bg-white rounded shadow">
        <thead className="bg-slate-100 text-sm">
          <tr>
            <th className="text-left p-3">Nome</th>
            <th className="text-left p-3">Cidade</th>
            <th className="text-left p-3">Status</th>
            <th className="text-left p-3">Limite/dia</th>
            <th className="text-left p-3">Delay (s)</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {campaigns.map(c => (
            <tr key={c.id} className="border-t">
              <td className="p-3">
                <Link className="text-blue-600 hover:underline" to={`/campaigns/${c.id}`}>{c.name}</Link>
                {c.parent_campaign_id && (
                  <span className="ml-2 text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
                    ↳ follow-up de #{c.parent_campaign_id}
                  </span>
                )}
              </td>
              <td className="p-3">{c.city || "-"}</td>
              <td className="p-3"><StatusBadge value={c.status} /></td>
              <td className="p-3">{renderEditable(c, "daily_limit")}</td>
              <td className="p-3">{renderEditable(c, "delay_seconds")}</td>
              <td className="p-3 text-right space-x-2">
                {c.status !== "active" &&
                  <button onClick={() => updateStatus(c.id, "active")} className="text-emerald-600 text-sm">Ativar</button>}
                {c.status === "active" &&
                  <button onClick={() => updateStatus(c.id, "paused")} className="text-yellow-600 text-sm">Pausar</button>}
                <button onClick={() => remove(c.id)} className="text-red-600 text-sm">Excluir</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="text-xs text-slate-500 mt-2">💡 Clique no número de limite ou delay para editar direto.</div>
    </div>
  );
}
