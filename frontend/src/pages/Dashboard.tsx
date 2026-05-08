import { useEffect, useState } from "react";
import { api, type DashboardMetrics } from "../lib/api";

export default function Dashboard() {
  const [m, setM] = useState<DashboardMetrics | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    const load = () =>
      api.get<DashboardMetrics>("/metrics").then(setM).catch((e) => setErr(String(e)));
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  if (err) return <div className="text-red-600">{err}</div>;
  if (!m) return <div>carregando...</div>;

  const cards = [
    { label: "Enviadas hoje", value: m.sent_today, color: "bg-blue-50 text-blue-700" },
    { label: "Entregues", value: m.delivered_today, color: "bg-indigo-50 text-indigo-700" },
    { label: "Lidas", value: m.read_today, color: "bg-emerald-50 text-emerald-700" },
    { label: "Falhas", value: m.failed_today, color: "bg-red-50 text-red-700" },
    { label: "Na fila", value: m.pending_queue, color: "bg-slate-100 text-slate-700" },
    { label: "Campanhas ativas", value: m.active_campaigns, color: "bg-amber-50 text-amber-700" },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-3 gap-4">
        {cards.map((c) => (
          <div key={c.label} className={`p-6 rounded-lg ${c.color}`}>
            <div className="text-sm">{c.label}</div>
            <div className="text-4xl font-bold mt-2">{c.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
