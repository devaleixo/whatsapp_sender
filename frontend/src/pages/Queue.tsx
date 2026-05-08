import { useEffect, useState } from "react";
import { api, type QueueItem } from "../lib/api";
import { fmtDateTime } from "../lib/datetime";

export default function Queue() {
  const [items, setItems] = useState<QueueItem[]>([]);

  const load = () => api.get<QueueItem[]>("/queue").then(setItems);
  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  const clear = async () => {
    if (!confirm("Limpar toda a fila?")) return;
    await api.del("/queue");
    load();
  };

  const removeItem = async (id: number) => {
    await api.del(`/queue/${id}`);
    load();
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Fila de Envios</h1>
        <button onClick={clear} className="text-red-600 text-sm">Limpar fila</button>
      </div>
      <div className="bg-white rounded shadow">
        <table className="w-full">
          <thead className="bg-slate-100 text-sm">
            <tr>
              <th className="text-left p-3">#</th>
              <th className="text-left p-3">Contato</th>
              <th className="text-left p-3">Template</th>
              <th className="text-left p-3">Agendado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map(i => (
              <tr key={i.id} className="border-t text-sm">
                <td className="p-3">{i.id}</td>
                <td className="p-3">contact #{i.contact_id}</td>
                <td className="p-3">template #{i.template_id}</td>
                <td className="p-3 text-xs">{fmtDateTime(i.scheduled_for)}</td>
                <td className="p-3 text-right">
                  <button onClick={() => removeItem(i.id)} className="text-red-600 text-sm">Remover</button>
                </td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={5} className="p-6 text-center text-slate-500">Fila vazia</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
