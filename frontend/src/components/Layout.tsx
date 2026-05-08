import { NavLink } from "react-router-dom";
import type { ReactNode } from "react";

const nav = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/campaigns", label: "Campanhas" },
  { to: "/templates", label: "Templates" },
  { to: "/types", label: "Tipos" },
  { to: "/queue", label: "Fila" },
  { to: "/inbox", label: "Inbox" },
  { to: "/bot", label: "Bot" },
  { to: "/instance", label: "WhatsApp" },
  { to: "/settings", label: "Configurações" },
];

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex">
      <aside className="w-56 bg-slate-900 text-slate-100 flex flex-col">
        <div className="p-4 font-bold text-lg border-b border-slate-700">WA Sender</div>
        <nav className="flex-1 p-2 space-y-1">
          {nav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded text-sm ${
                  isActive ? "bg-emerald-600 text-white" : "hover:bg-slate-800"
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 p-6 overflow-auto">{children}</main>
    </div>
  );
}
