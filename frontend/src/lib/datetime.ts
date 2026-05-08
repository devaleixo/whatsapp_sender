// Backend envia datetime sem timezone info (ex.: "2026-04-24T14:05:16.789").
// O navegador parseia ISO sem TZ como UTC — errado pra nós. O backend já roda
// em America/Sao_Paulo, então tratamos como hora local.

function parseLocal(s: string | null | undefined): Date | null {
  if (!s) return null;
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d+))?/);
  if (!m) return new Date(s);
  const [, y, mo, d, h, mi, sec, ms] = m;
  return new Date(+y, +mo - 1, +d, +h, +mi, +sec, ms ? +ms.substring(0, 3) : 0);
}

export function fmtDateTime(s: string | null | undefined): string {
  const d = parseLocal(s);
  if (!d) return "-";
  return d.toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" });
}

export function fmtTime(s: string | null | undefined): string {
  const d = parseLocal(s);
  if (!d) return "-";
  return d.toLocaleTimeString("pt-BR", { timeZone: "America/Sao_Paulo" });
}

export function fmtDate(s: string | null | undefined): string {
  const d = parseLocal(s);
  if (!d) return "-";
  return d.toLocaleDateString("pt-BR", { timeZone: "America/Sao_Paulo" });
}
