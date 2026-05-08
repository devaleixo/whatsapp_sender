import { useEffect, useState } from "react";
import { api, type RecipientType, type Template } from "../lib/api";

export default function Templates() {
  const [types, setTypes] = useState<RecipientType[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [editing, setEditing] = useState<Template | null>(null);
  const [form, setForm] = useState({ recipient_type_id: 0, name: "", body: "" });
  const [err, setErr] = useState<string | null>(null);

  const load = async () => {
    setTypes(await api.get<RecipientType[]>("/recipient-types"));
    setTemplates(await api.get<Template[]>("/templates"));
  };
  useEffect(() => { load(); }, []);

  const variables = (body: string) =>
    Array.from(body.matchAll(/\{(\w+)\}/g)).map(m => m[1]);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    const payload = { ...form, variables: variables(form.body), active: true };
    try {
      if (editing) await api.put(`/templates/${editing.id}`, payload);
      else await api.post("/templates", payload);
      setEditing(null);
      setForm({ recipient_type_id: 0, name: "", body: "" });
      load();
    } catch (e: any) { setErr(String(e)); }
  };

  const edit = (t: Template) => {
    setEditing(t);
    setForm({ recipient_type_id: t.recipient_type_id, name: t.name, body: t.body });
  };

  const remove = async (id: number) => {
    if (!confirm("Excluir template?")) return;
    await api.del(`/templates/${id}`);
    load();
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Templates</h1>
      <form onSubmit={save} className="bg-white p-4 rounded shadow mb-6">
        <div className="grid grid-cols-2 gap-3 mb-3">
          <select className="border rounded px-3 py-2" value={form.recipient_type_id}
                  onChange={e => setForm({ ...form, recipient_type_id: Number(e.target.value) })} required>
            <option value={0}>Selecione tipo...</option>
            {types.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
          <input className="border rounded px-3 py-2" placeholder="Nome do template" value={form.name}
                 onChange={e => setForm({ ...form, name: e.target.value })} required />
        </div>
        <textarea className="border rounded px-3 py-2 w-full" rows={8} placeholder="Corpo. Use {nome}, {endereco}, {avaliacao}, {website}..."
                  value={form.body} onChange={e => setForm({ ...form, body: e.target.value })} required />
        <div className="text-xs text-slate-500 mt-1">Variáveis detectadas: {variables(form.body).join(", ") || "(nenhuma)"}</div>
        <div className="flex gap-2 mt-3">
          <button className="bg-emerald-600 text-white px-4 py-2 rounded">{editing ? "Atualizar" : "Criar"}</button>
          {editing && <button type="button" className="px-4 py-2" onClick={() => { setEditing(null); setForm({ recipient_type_id: 0, name: "", body: "" }); }}>Cancelar</button>}
        </div>
      </form>
      {err && <div className="text-red-600 mb-4">{err}</div>}
      <div className="space-y-3">
        {templates.map(t => (
          <div key={t.id} className="bg-white p-4 rounded shadow">
            <div className="flex justify-between items-start">
              <div>
                <div className="font-medium">{t.name}</div>
                <div className="text-xs text-slate-500">
                  tipo #{t.recipient_type_id} · variáveis: {t.variables.join(", ") || "-"}
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => edit(t)} className="text-blue-600 text-sm">Editar</button>
                <button onClick={() => remove(t.id)} className="text-red-600 text-sm">Excluir</button>
              </div>
            </div>
            <pre className="mt-2 text-sm bg-slate-50 p-3 rounded whitespace-pre-wrap">{t.body}</pre>
          </div>
        ))}
      </div>
    </div>
  );
}
