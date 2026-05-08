import { useEffect, useState } from "react";
import { api, type RecipientType } from "../lib/api";

export default function RecipientTypes() {
  const [types, setTypes] = useState<RecipientType[]>([]);
  const [slug, setSlug] = useState("");
  const [name, setName] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const load = () => api.get<RecipientType[]>("/recipient-types").then(setTypes);
  useEffect(() => { load(); }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr(null);
    try {
      await api.post("/recipient-types", { slug, name });
      setSlug(""); setName("");
      load();
    } catch (e: any) { setErr(String(e)); }
  };

  const remove = async (id: number) => {
    if (!confirm("Excluir tipo?")) return;
    await api.del(`/recipient-types/${id}`);
    load();
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Tipos de Destinatário</h1>
      <form onSubmit={create} className="flex gap-2 mb-6">
        <input className="border rounded px-3 py-2" placeholder="slug (advocacia)" value={slug} onChange={e => setSlug(e.target.value)} required />
        <input className="border rounded px-3 py-2 flex-1" placeholder="Nome (Escritório de Advocacia)" value={name} onChange={e => setName(e.target.value)} required />
        <button className="bg-emerald-600 text-white px-4 py-2 rounded">Adicionar</button>
      </form>
      {err && <div className="text-red-600 mb-4">{err}</div>}
      <table className="w-full bg-white rounded shadow">
        <thead className="bg-slate-100 text-sm">
          <tr><th className="text-left p-3">Slug</th><th className="text-left p-3">Nome</th><th></th></tr>
        </thead>
        <tbody>
          {types.map(t => (
            <tr key={t.id} className="border-t">
              <td className="p-3 font-mono text-sm">{t.slug}</td>
              <td className="p-3">{t.name}</td>
              <td className="p-3 text-right">
                <button onClick={() => remove(t.id)} className="text-red-600 text-sm">Excluir</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
