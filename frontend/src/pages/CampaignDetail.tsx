import { useEffect, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { api, type Campaign, type Contact, type Template } from "../lib/api";
import StatusBadge from "../components/StatusBadge";

type Stats = {
  total_contacts: number;
  sent: number;
  failed: number;
  queued: number;
  is_remarketing: boolean;
  chain_ids?: number[];
  eligible_for_followup?: number;
  replied_excluded?: number;
};

export default function CampaignDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const cid = Number(id);
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [followups, setFollowups] = useState<Campaign[]>([]);
  const [manual, setManual] = useState({ name: "", phone: "" });
  const [msg, setMsg] = useState<string | null>(null);
  const [showFollowup, setShowFollowup] = useState(false);
  const [followupForm, setFollowupForm] = useState({
    name: "",
    template_id: 0,
    daily_limit: 20,
    delay_seconds: 60,
    remarketing_delay_hours: 48,
    exclude_replied: true,
    exclude_replied_scope: "phone",
    max_followups: 1,
  });
  const fileRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    const c = await api.get<Campaign>(`/campaigns/${cid}`);
    setCampaign(c);
    setContacts(await api.get(`/campaigns/${cid}/contacts`));
    setStats(await api.get(`/campaigns/${cid}/stats`));
    const all = await api.get<Campaign[]>("/campaigns");
    setFollowups(all.filter(x => x.parent_campaign_id === cid));
    setTemplates(
      (await api.get<Template[]>("/templates")).filter(t => t.recipient_type_id === c.recipient_type_id)
    );
  };
  useEffect(() => { if (cid) load(); }, [cid]);

  const upload = async () => {
    const f = fileRef.current?.files?.[0];
    if (!f) return;
    setMsg("enviando...");
    try {
      const r = await api.upload<{ imported: number; skipped: number; invalid: number }>(
        `/campaigns/${cid}/contacts/import`, f);
      setMsg(`importados: ${r.imported}, pulados: ${r.skipped}, inválidos: ${r.invalid}`);
      if (fileRef.current) fileRef.current.value = "";
      load();
    } catch (e: any) { setMsg(String(e)); }
  };

  const addContact = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post(`/campaigns/${cid}/contacts`, manual);
      setManual({ name: "", phone: "" });
      load();
    } catch (e: any) { setMsg(String(e)); }
  };

  const enqueue = async () => {
    const r = await api.post<{ enqueued: number; skipped: number }>(`/campaigns/${cid}/enqueue`);
    setMsg(`enfileirados: ${r.enqueued}, pulados: ${r.skipped}`);
    load();
  };

  const createFollowup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!followupForm.template_id) { setMsg("escolha um template"); return; }
    try {
      const created = await api.post<Campaign>(`/campaigns/${cid}/remarketing`, followupForm);
      setShowFollowup(false);
      navigate(`/campaigns/${created.id}`);
    } catch (e: any) { setMsg(String(e)); }
  };

  if (!campaign) return <div>carregando...</div>;

  const isRemarketing = campaign.parent_campaign_id !== null;

  return (
    <div>
      <Link to="/campaigns" className="text-sm text-slate-500">← voltar</Link>
      <h1 className="text-2xl font-bold mt-2 mb-1">{campaign.name}</h1>
      {isRemarketing && (
        <div className="mb-3 text-sm">
          <span className="bg-purple-100 text-purple-700 px-2 py-0.5 rounded">
            follow-up de{" "}
            <Link to={`/campaigns/${campaign.parent_campaign_id}`} className="underline">
              campanha #{campaign.parent_campaign_id}
            </Link>
          </span>
          <span className="ml-2 text-slate-500">
            delay {campaign.remarketing_delay_hours}h ·{" "}
            {campaign.exclude_replied ? `exclui quem respondeu (${campaign.exclude_replied_scope})` : "sem filtro de reply"}
          </span>
        </div>
      )}
      <div className="flex gap-3 mb-6">
        <StatusBadge value={campaign.status} />
        <span className="text-sm text-slate-500">limite: {campaign.daily_limit}/dia · delay: {campaign.delay_seconds}s</span>
      </div>

      {stats && (
        <div className={`grid ${stats.is_remarketing ? "grid-cols-6" : "grid-cols-4"} gap-3 mb-6`}>
          <div className="bg-white p-3 rounded shadow"><div className="text-xs text-slate-500">{stats.is_remarketing ? "Contatos (raiz)" : "Contatos"}</div><div className="text-2xl">{stats.total_contacts}</div></div>
          <div className="bg-white p-3 rounded shadow"><div className="text-xs text-slate-500">Enviados</div><div className="text-2xl">{stats.sent}</div></div>
          <div className="bg-white p-3 rounded shadow"><div className="text-xs text-slate-500">Falhas</div><div className="text-2xl">{stats.failed}</div></div>
          <div className="bg-white p-3 rounded shadow"><div className="text-xs text-slate-500">Na fila</div><div className="text-2xl">{stats.queued}</div></div>
          {stats.is_remarketing && (
            <>
              <div className="bg-white p-3 rounded shadow"><div className="text-xs text-slate-500">Elegíveis</div><div className="text-2xl text-emerald-600">{stats.eligible_for_followup ?? 0}</div></div>
              <div className="bg-white p-3 rounded shadow"><div className="text-xs text-slate-500">Excluídos (responderam)</div><div className="text-2xl text-purple-600">{stats.replied_excluded ?? 0}</div></div>
            </>
          )}
        </div>
      )}

      {!isRemarketing && (
        <>
          <div className="bg-white p-4 rounded shadow mb-4">
            <div className="font-medium mb-2">Importar XLSX</div>
            <div className="text-xs text-slate-500 mb-2">Formato: Nome | Telefone | Endereço | Avaliação | Website (1ª linha é cabeçalho)</div>
            <div className="flex gap-2">
              <input type="file" ref={fileRef} accept=".xlsx" className="flex-1" />
              <button onClick={upload} className="bg-emerald-600 text-white px-4 py-2 rounded">Importar</button>
            </div>
          </div>

          <form onSubmit={addContact} className="bg-white p-4 rounded shadow mb-4 flex gap-2">
            <input className="border rounded px-3 py-2 flex-1" placeholder="Nome" value={manual.name}
                   onChange={e => setManual({ ...manual, name: e.target.value })} required />
            <input className="border rounded px-3 py-2" placeholder="Telefone" value={manual.phone}
                   onChange={e => setManual({ ...manual, phone: e.target.value })} required />
            <button className="bg-slate-600 text-white px-4 py-2 rounded">Adicionar</button>
          </form>
        </>
      )}

      <div className="flex gap-3 mb-4">
        <button onClick={enqueue} className="bg-indigo-600 text-white px-4 py-2 rounded">
          {isRemarketing ? "Reavaliar elegíveis" : "Enfileirar pendentes"}
        </button>
        <button onClick={() => setShowFollowup(s => !s)} className="bg-purple-600 text-white px-4 py-2 rounded">
          {showFollowup ? "Cancelar" : "Criar follow-up"}
        </button>
        {msg && <div className="text-sm text-slate-600 self-center">{msg}</div>}
      </div>

      {showFollowup && (
        <form onSubmit={createFollowup} className="bg-white p-4 rounded shadow mb-6 grid grid-cols-3 gap-3">
          <input className="border rounded px-3 py-2 col-span-3" placeholder={`Nome (default: "${campaign.name} — follow-up")`}
                 value={followupForm.name}
                 onChange={e => setFollowupForm({ ...followupForm, name: e.target.value })} />
          <select className="border rounded px-3 py-2 col-span-3" value={followupForm.template_id}
                  onChange={e => setFollowupForm({ ...followupForm, template_id: Number(e.target.value) })} required>
            <option value={0}>Template do follow-up...</option>
            {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
          <label className="text-sm">Atraso mínimo (h)
            <input type="number" min={1} className="border rounded px-3 py-2 w-full"
                   value={followupForm.remarketing_delay_hours}
                   onChange={e => setFollowupForm({ ...followupForm, remarketing_delay_hours: Number(e.target.value) })} />
          </label>
          <label className="text-sm">Limite/dia
            <input type="number" min={1} className="border rounded px-3 py-2 w-full"
                   value={followupForm.daily_limit}
                   onChange={e => setFollowupForm({ ...followupForm, daily_limit: Number(e.target.value) })} />
          </label>
          <label className="text-sm">Delay entre envios (s)
            <input type="number" min={1} className="border rounded px-3 py-2 w-full"
                   value={followupForm.delay_seconds}
                   onChange={e => setFollowupForm({ ...followupForm, delay_seconds: Number(e.target.value) })} />
          </label>
          <label className="text-sm flex items-center gap-2 col-span-2">
            <input type="checkbox" checked={followupForm.exclude_replied}
                   onChange={e => setFollowupForm({ ...followupForm, exclude_replied: e.target.checked })} />
            Excluir quem respondeu
          </label>
          <label className="text-sm">Escopo do reply
            <select className="border rounded px-3 py-2 w-full" value={followupForm.exclude_replied_scope}
                    onChange={e => setFollowupForm({ ...followupForm, exclude_replied_scope: e.target.value })}>
              <option value="phone">por telefone (cruza campanhas)</option>
              <option value="contact">por contato</option>
            </select>
          </label>
          <button className="col-span-3 bg-purple-600 text-white px-4 py-2 rounded">Criar follow-up</button>
        </form>
      )}

      {followups.length > 0 && (
        <div className="bg-white rounded shadow mb-6 p-3">
          <div className="font-medium mb-2 text-sm">Follow-ups desta campanha</div>
          <ul className="text-sm">
            {followups.map(f => (
              <li key={f.id}>
                <Link to={`/campaigns/${f.id}`} className="text-blue-600 hover:underline">{f.name}</Link>
                <span className="ml-2 text-slate-500">· {f.status} · delay {f.remarketing_delay_hours}h</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="bg-white rounded shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-100 text-sm">
            <tr>
              <th className="text-left p-3">Nome</th>
              <th className="text-left p-3">Telefone</th>
              <th className="text-left p-3">E.164</th>
              <th className="text-left p-3">WhatsApp?</th>
            </tr>
          </thead>
          <tbody>
            {contacts.map(c => (
              <tr key={c.id} className="border-t text-sm">
                <td className="p-3">{c.name}</td>
                <td className="p-3">{c.phone}</td>
                <td className="p-3 font-mono text-xs">{c.e164_phone}</td>
                <td className="p-3"><StatusBadge value={c.has_whatsapp} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
