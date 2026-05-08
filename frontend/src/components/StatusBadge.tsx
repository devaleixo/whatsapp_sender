const STYLES: Record<string, string> = {
  draft: "bg-slate-200 text-slate-700",
  active: "bg-emerald-100 text-emerald-700",
  paused: "bg-yellow-100 text-yellow-700",
  done: "bg-slate-100 text-slate-500",
  pending: "bg-slate-200 text-slate-700",
  sent: "bg-blue-100 text-blue-700",
  delivered: "bg-indigo-100 text-indigo-700",
  read: "bg-emerald-100 text-emerald-700",
  failed: "bg-red-100 text-red-700",
  bot: "bg-purple-100 text-purple-700",
  human: "bg-amber-100 text-amber-700",
  yes: "bg-emerald-100 text-emerald-700",
  no: "bg-red-100 text-red-700",
  unknown: "bg-slate-200 text-slate-600",
};

export default function StatusBadge({ value }: { value: string }) {
  const cls = STYLES[value] || "bg-slate-200 text-slate-700";
  return <span className={`inline-block px-2 py-0.5 text-xs rounded ${cls}`}>{value}</span>;
}
