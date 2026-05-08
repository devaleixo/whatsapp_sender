import { useEffect, useState } from "react";
import { api, type AppSettings } from "../lib/api";

const WEEKDAYS = [
  { n: 0, label: "Seg" },
  { n: 1, label: "Ter" },
  { n: 2, label: "Qua" },
  { n: 3, label: "Qui" },
  { n: 4, label: "Sex" },
  { n: 5, label: "Sáb" },
  { n: 6, label: "Dom" },
];

function parseDays(csv: string): Set<number> {
  return new Set(
    csv.split(",").map(s => s.trim()).filter(s => /^[0-6]$/.test(s)).map(Number)
  );
}

export default function SettingsPage() {
  const [cfg, setCfg] = useState<AppSettings | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.get<AppSettings>("/settings").then(setCfg).catch(e => setErr(String(e)));
  }, []);

  const toggleDay = (n: number) => {
    if (!cfg) return;
    const days = parseDays(cfg.send_days);
    if (days.has(n)) days.delete(n); else days.add(n);
    const csv = [...days].sort((a, b) => a - b).join(",");
    setCfg({ ...cfg, send_days: csv });
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cfg) return;
    setErr(null); setMsg(null);
    try {
      const saved = await api.put<AppSettings>("/settings", cfg);
      setCfg(saved);
      setMsg("salvo");
      setTimeout(() => setMsg(null), 2000);
    } catch (e: any) { setErr(String(e)); }
  };

  if (!cfg) return <div>carregando...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Configurações de Envio</h1>
      <form onSubmit={save} className="bg-white p-6 rounded shadow space-y-5 max-w-2xl">
        <div>
          <div className="font-medium mb-2">Janela de envio em massa</div>
          <div className="text-xs text-slate-500 mb-3">
            O worker só envia mensagens entre esses horários (hora local da máquina).
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm mb-1">Hora início (0–23)</label>
              <input type="number" min={0} max={23} className="border rounded px-3 py-2 w-full"
                     value={cfg.send_window_start}
                     onChange={e => setCfg({ ...cfg, send_window_start: Number(e.target.value) })} />
            </div>
            <div>
              <label className="block text-sm mb-1">Hora fim (1–24)</label>
              <input type="number" min={1} max={24} className="border rounded px-3 py-2 w-full"
                     value={cfg.send_window_end}
                     onChange={e => setCfg({ ...cfg, send_window_end: Number(e.target.value) })} />
            </div>
          </div>
          <div className="text-xs text-slate-500 mt-2">
            Ex.: 8 e 18 = envia das 08:00 às 17:59. Fora dessa janela, a fila acumula e manda no próximo dia.
          </div>
        </div>

        <div>
          <div className="font-medium mb-2">Dias da semana</div>
          <div className="text-xs text-slate-500 mb-3">
            Em quais dias o worker pode enviar. Em dias desmarcados a fila acumula.
          </div>
          <div className="flex flex-wrap gap-2">
            {WEEKDAYS.map(d => {
              const selected = parseDays(cfg.send_days).has(d.n);
              return (
                <button
                  key={d.n}
                  type="button"
                  onClick={() => toggleDay(d.n)}
                  className={
                    "px-4 py-2 rounded border text-sm " +
                    (selected
                      ? "bg-emerald-600 text-white border-emerald-600"
                      : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50")
                  }
                >
                  {d.label}
                </button>
              );
            })}
          </div>
        </div>

        <div>
          <div className="font-medium mb-2">Indicador "digitando..."</div>
          <div className="text-xs text-slate-500 mb-3">
            Antes de enviar, mostra ao destinatário que você está digitando, por X segundos.
            Faz o envio parecer mais natural/humano. <strong>0 = desativado</strong> (envia direto).
          </div>
          <label className="block text-sm mb-1">Segundos (0–30)</label>
          <input type="number" min={0} max={30} className="border rounded px-3 py-2 w-40"
                 value={cfg.typing_delay_seconds}
                 onChange={e => setCfg({ ...cfg, typing_delay_seconds: Number(e.target.value) })} />
          <div className="text-xs text-slate-500 mt-2">
            Aplica a envios em massa, respostas do bot e mensagens manuais do inbox.
          </div>
        </div>

        <div>
          <div className="font-medium mb-2">Intervalo do worker</div>
          <div className="text-xs text-slate-500 mb-3">
            A cada quantos segundos o worker verifica a fila. Cada tick manda no máximo 1 msg por campanha,
            respeitando o delay de cada campanha.
          </div>
          <label className="block text-sm mb-1">Segundos (10–3600)</label>
          <input type="number" min={10} max={3600} className="border rounded px-3 py-2 w-40"
                 value={cfg.worker_tick_seconds}
                 onChange={e => setCfg({ ...cfg, worker_tick_seconds: Number(e.target.value) })} />
          <div className="text-xs text-slate-500 mt-2">
            Mudança só tem efeito após reiniciar o backend: <code className="bg-slate-100 px-1">docker compose restart backend</code>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button className="bg-emerald-600 text-white px-6 py-2 rounded">Salvar</button>
          {msg && <div className="text-sm text-emerald-600">{msg}</div>}
          {err && <div className="text-sm text-red-600">{err}</div>}
        </div>
      </form>

      <div className="mt-6 bg-amber-50 border border-amber-200 text-amber-800 p-4 rounded max-w-2xl text-sm">
        <strong>Nota:</strong> a janela de envio em massa é separada do horário do bot respondedor
        (que fica em <strong>Bot</strong>, configurado por tipo de destinatário).
      </div>
    </div>
  );
}
