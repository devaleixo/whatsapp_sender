import { useEffect, useState } from "react";
import { api, type InstanceStatus } from "../lib/api";
import StatusBadge from "../components/StatusBadge";

type WebhookInfo = {
  current_url: string | null;
  expected_url: string;
  correct: boolean;
  raw: unknown;
};

export default function Instance() {
  const [status, setStatus] = useState<InstanceStatus | null>(null);
  const [webhook, setWebhook] = useState<WebhookInfo | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = () =>
    api.get<InstanceStatus>("/instance/status")
      .then(s => { setStatus(s); setErr(null); })
      .catch(e => setErr(String(e)));

  const loadWebhook = () =>
    api.get<WebhookInfo>("/instance/webhook")
      .then(setWebhook)
      .catch(() => setWebhook(null));

  useEffect(() => {
    load();
    loadWebhook();
    const t = setInterval(() => { load(); loadWebhook(); }, 5000);
    return () => clearInterval(t);
  }, []);

  const restart = async () => {
    await api.post("/instance/restart");
    load();
  };

  const registerWebhook = async () => {
    setMsg("registrando...");
    try {
      const r = await api.post<{ status: string; url: string; changed: boolean }>("/instance/webhook/register");
      setMsg(r.status === "ok" ? (r.changed ? "webhook atualizado" : "já estava ok") : "erro");
      loadWebhook();
    } catch (e: any) { setMsg(String(e)); }
    setTimeout(() => setMsg(null), 3000);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">WhatsApp</h1>
      {err && <div className="bg-red-50 text-red-700 p-3 rounded text-sm">Não foi possível conectar ao Evolution: {err}</div>}

      {status && (
        <div className="bg-white p-6 rounded shadow max-w-xl">
          <div className="flex justify-between items-center mb-4">
            <div>
              <div className="text-sm text-slate-500">Instância</div>
              <div className="font-mono">{status.name}</div>
            </div>
            <StatusBadge value={status.connected ? "yes" : "no"} />
          </div>
          {!status.connected && status.qrcode_base64 && (
            <div>
              <div className="text-sm mb-2">Escaneie com WhatsApp &gt; Aparelhos Conectados</div>
              <img src={status.qrcode_base64} alt="QR Code" className="border rounded" />
            </div>
          )}
          {!status.connected && !status.qrcode_base64 && (
            <div className="text-sm text-slate-500">Aguardando QR Code...</div>
          )}
          <button onClick={restart} className="mt-4 bg-slate-600 text-white px-4 py-2 rounded text-sm">Reiniciar instância</button>
        </div>
      )}

      <div className="bg-white p-6 rounded shadow max-w-xl">
        <div className="flex justify-between items-center mb-3">
          <div className="font-medium">Webhook (mensagens recebidas)</div>
          {webhook && <StatusBadge value={webhook.correct ? "yes" : "no"} />}
        </div>
        {webhook ? (
          <div className="space-y-2 text-sm">
            <div>
              <span className="text-slate-500">Esperado:</span>
              <div className="font-mono text-xs break-all">{webhook.expected_url}</div>
            </div>
            <div>
              <span className="text-slate-500">Atual:</span>
              <div className="font-mono text-xs break-all">{webhook.current_url || "(não registrado)"}</div>
            </div>
            {!webhook.correct && (
              <div className="bg-amber-50 text-amber-800 p-2 rounded text-xs">
                Webhook não está apontando pro backend. Clique em "Registrar" pra corrigir — sem isso,
                mensagens recebidas no WhatsApp <strong>não chegam no Inbox</strong>.
              </div>
            )}
          </div>
        ) : (
          <div className="text-sm text-slate-500">carregando...</div>
        )}
        <div className="mt-4 flex items-center gap-3">
          <button onClick={registerWebhook} className="bg-emerald-600 text-white px-4 py-2 rounded text-sm">
            Registrar webhook
          </button>
          {msg && <span className="text-sm text-slate-600">{msg}</span>}
        </div>
      </div>
    </div>
  );
}
