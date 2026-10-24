const mxn = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", minimumFractionDigits: 2 });
const mxn0 = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 });

export const money = (v: number | null | undefined) => (v == null ? "—" : mxn.format(v));
export const money0 = (v: number | null | undefined) => (v == null ? "—" : mxn0.format(v));
export const moneyShort = (v: number | null | undefined) => {
  if (v == null) return "—";
  if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)} M`;
  if (Math.abs(v) >= 10_000) return `$${(v / 1_000).toFixed(1)} k`;
  return money(v);
};
export const pct = (v: number | null | undefined, digits = 0) => (v == null ? "—" : `${(v * 100).toFixed(digits)} %`);
export const num = (v: number | null | undefined, digits = 1) =>
  v == null ? "—" : v.toLocaleString("es-MX", { minimumFractionDigits: digits, maximumFractionDigits: digits });
export const hours = (v: number | null | undefined) => (v == null ? "—" : `${num(v, 2)} h`);

const dateFmt = new Intl.DateTimeFormat("es-MX", { day: "2-digit", month: "short", year: "numeric" });
const dateTimeFmt = new Intl.DateTimeFormat("es-MX", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
const monthFmt = new Intl.DateTimeFormat("es-MX", { month: "short", year: "numeric" });

/** "2026-10-23" se interpreta como fecha local (no UTC). */
function parse(v: string) {
  return /^\d{4}-\d{2}-\d{2}$/.test(v) ? new Date(`${v}T12:00:00`) : new Date(v);
}
export const date = (v: string | null | undefined) => (v ? dateFmt.format(parse(v)) : "—");
export const dateTime = (v: string | null | undefined) => (v ? dateTimeFmt.format(parse(v)) : "—");
export const month = (yyyyMm: string) => monthFmt.format(new Date(`${yyyyMm}-15T12:00:00`));
export const isoDate = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

export function duration(h: number) {
  const totalSec = Math.max(0, Math.round(h * 3600));
  const hh = Math.floor(totalSec / 3600);
  const mm = Math.floor((totalSec % 3600) / 60);
  const ss = totalSec % 60;
  return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}:${String(ss).padStart(2, "0")}`;
}
