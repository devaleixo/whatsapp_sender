import { useEffect, useState } from "react";
import { api, type BotConfig, type RecipientType } from "../lib/api";

const EMPTY: BotConfig = {
  recipient_type_id: 0,
  system_prompt: "",
  model: null,
  temperature: 0.7,
  handoff_keywords: [],
  active_hours_start: 8,
  active_hours_end: 18,
  enabled: false,
  provider: "stub",
};

export default function BotConfigPage() {
  const [types, setTypes] = useState<RecipientType[]>([]);
  const [selectedType, setSelectedType] = useState<number>(0);
  const [cfg, setCfg] = useState<BotConfig>(EMPTY);
  const [keywordsText, setKeywordsText] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    api.get<RecipientType[]>("/recipient-types").then(t => {
      setTypes(t);
      if (t.length > 0 && !selectedType) setSelectedType(t[0].id);
    });
  }, []);

  useEffect(() => {
    if (!selectedType) return;
    api.get<BotConfig>(`/bot-configs/by-type/${selectedType}`)
      .then(c => {
        setCfg(c);
        setKeywordsText((c.handoff_keywords || []).join(", "));
      })
      .catch(() => {
        setCfg({ ...EMPTY, recipient_type_id: selectedType });
        setKeywordsText("");
      });
  }, [selectedType]);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    const payload = {
      ...cfg,
      recipient_type_id: selectedType,
      handoff_keywords: keywordsText.split(",").map(s => s.trim()).filter(Boolean),
    };
    try {
      const saved = await api.put<BotConfig>(`/bot-configs/by-type/${selectedType}`, payload);
      setCfg(saved);
      setMsg("salvo");
      setTimeout(() => setMsg(null), 2000);
    } catch (e: any) { setMsg(String(e)); }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Configuração do Bot</h1>
      <div className="mb-4">
        <label className="block text-sm mb-1">Tipo de destinatário</label>
        <select className="border rounded px-3 py-2" value={selectedType}
                onChange={e => setSelectedType(Number(e.target.value))}>
          {types.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
      </div>

      <form onSubmit={save} className="bg-white p-6 rounded shadow space-y-4 max-w-3xl">
        <div>
          <label className="block text-sm mb-1">System prompt (persona / regras)</label>
          <textarea className="border rounded px-3 py-2 w-full" rows={10}
                    value={cfg.system_prompt}
                    onChange={e => setCfg({ ...cfg, system_prompt: e.target.value })} />
        </div>

        <div>
          <label className="block text-sm mb-1">Keywords de handoff (separadas por vírgula)</label>
          <input className="border rounded px-3 py-2 w-full"
                 placeholder="quero contratar, reunião, proposta, preço..."
                 value={keywordsText} onChange={e => setKeywordsText(e.target.value)} />
          <div className="text-xs text-slate-500 mt-1">Ao detectar qualquer uma, bot para e envia alerta no seu WhatsApp.</div>
        </div>

        <div className="grid grid-cols-4 gap-3">
          <div>
            <label className="block text-sm mb-1">Hora início</label>
            <input type="number" min={0} max={23} className="border rounded px-3 py-2 w-full"
                   value={cfg.active_hours_start}
                   onChange={e => setCfg({ ...cfg, active_hours_start: Number(e.target.value) })} />
          </div>
          <div>
            <label className="block text-sm mb-1">Hora fim</label>
            <input type="number" min={0} max={24} className="border rounded px-3 py-2 w-full"
                   value={cfg.active_hours_end}
                   onChange={e => setCfg({ ...cfg, active_hours_end: Number(e.target.value) })} />
          </div>
          <div>
            <label className="block text-sm mb-1">Provider LLM</label>
            <select className="border rounded px-3 py-2 w-full" value={cfg.provider}
                    onChange={e => setCfg({ ...cfg, provider: e.target.value })}>
              <option value="stub">stub (desativado)</option>
              <option value="claude">claude (requer implementação)</option>
              <option value="openai">openai (requer implementação)</option>
              <option value="ollama">ollama (requer implementação)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm mb-1">Temperatura</label>
            <input type="number" step={0.1} min={0} max={2} className="border rounded px-3 py-2 w-full"
                   value={cfg.temperature}
                   onChange={e => setCfg({ ...cfg, temperature: Number(e.target.value) })} />
          </div>
        </div>

        <div>
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={cfg.enabled}
                   onChange={e => setCfg({ ...cfg, enabled: e.target.checked })} />
            <span>Bot ativo para este tipo</span>
          </label>
        </div>

        <div className="flex items-center gap-3">
          <button className="bg-emerald-600 text-white px-6 py-2 rounded">Salvar</button>
          {msg && <div className="text-sm text-slate-600">{msg}</div>}
        </div>
      </form>
    </div>
  );
}
