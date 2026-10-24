import { AlertTriangle, CalendarClock, ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import { Chart } from "../components/Chart";
import { Table } from "../components/Table";
import { Button, Card, ErrorState, InfoTip, Notice, PageHeader } from "../components/ui";
import { useChartColors } from "../lib/chartTheme";
import { barOption } from "../lib/charts";
import { date, isoDate, num, pct } from "../lib/format";
import { useApi } from "../lib/hooks";

interface Row { technician: string; ordenes: number; carga_horas: number; capacidad_horas: number; utilizacion: number; holgura_horas: number; sobrecarga: boolean }
interface Cap { week: string; rows: Row[]; overview: { week: string; rows: { technician: string; utilizacion: number; sobrecarga: boolean }[] }[] }

const short = (n: string) => n.split("·")[1]?.trim() ?? n;

export default function Capacidad() {
  const c = useChartColors();
  const [week, setWeek] = useState<string | null>(null);
  const { data, error, loading, reload } = useApi<Cap>("/api/capacity", { week });
  const shift = (d: number) => {
    const base = new Date(`${data?.week ?? isoDate(new Date())}T12:00:00`);
    base.setDate(base.getDate() + d * 7);
    setWeek(isoDate(base));
  };
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const over = data?.rows.filter((r) => r.sobrecarga) ?? [];

  return (
    <div>
      <PageHeader icon={CalendarClock} title="Carga vs. capacidad semanal" subtitle="Horas estándar programadas vs. horas disponibles por técnico"
        crumbs={[{ label: "Análisis" }, { label: "Capacidad" }]}
        actions={
          <div className="flex items-center gap-2">
            <Button size="sm" icon={ChevronLeft} onClick={() => shift(-1)} aria-label="Semana anterior" />
            <span className="min-w-40 text-center text-sm font-medium text-text">Semana del {data ? date(data.week) : "…"}</span>
            <Button size="sm" icon={ChevronRight} onClick={() => shift(1)} aria-label="Semana siguiente" />
            <Button size="sm" variant="ghost" onClick={() => setWeek(null)}>Hoy</Button>
          </div>
        } />
      {data && (over.length ? (
        <Notice kind="danger"><AlertTriangle size={14} className="mr-1 inline" aria-hidden />Sobrecarga: {over.map((r) => `${short(r.technician)} (${pct(r.utilizacion)}, ${num(-r.holgura_horas)} h de más)`).join(", ")}. Reasigna en Órdenes o usa Secuenciación.</Notice>
      ) : <Notice kind="success">Ningún técnico excede su capacidad esta semana.</Notice>)}
      <div className="mt-4 grid gap-4 lg:grid-cols-5">
        <Card className="lg:col-span-3" title={<span className="inline-flex items-center gap-1">Carga por técnico<InfoTip text="Capacidad = 6 días laborables × 8 h. Barras rojas = sobrecarga." formula="Utilización = Σ horas estándar programadas ÷ capacidad" /></span>}>
          <Chart loading={loading} ariaLabel="Carga vs capacidad" option={barOption(c, {
            categories: (data?.rows ?? []).map((r) => short(r.technician)), values: (data?.rows ?? []).map((r) => r.carga_horas),
            name: "Carga", format: (v) => `${num(v, 0)} h`, labels: true,
            colors: (data?.rows ?? []).map((r) => (r.sobrecarga ? c.bad : c.series[0])),
            refLine: data?.rows[0] ? { value: data.rows[0].capacidad_horas, label: `Capacidad ${data.rows[0].capacidad_horas} h` } : undefined,
          })} />
        </Card>
        <Card className="lg:col-span-2" title="Detalle">
          <Table rows={data?.rows} loading={loading} rowKey={(r) => r.technician} columns={[
            { key: "t", header: "Técnico", render: (r) => short(r.technician) },
            { key: "o", header: "Órd.", numeric: true, render: (r) => r.ordenes },
            { key: "c", header: "Carga", numeric: true, render: (r) => `${num(r.carga_horas)} h` },
            { key: "u", header: "Util.", numeric: true, render: (r) => <span className={r.sobrecarga ? "font-bold text-danger" : ""}>{r.sobrecarga && "⚠ "}{pct(r.utilizacion)}</span> },
          ]} />
        </Card>
      </div>
      <Card className="mt-4" title="Vista general (12 semanas)" actions={<span className="text-xs text-muted">Clic en una semana para verla</span>}>
        <div className="overflow-x-auto">
          <table className="table-base">
            <thead><tr><th>Semana</th>{data?.overview[0]?.rows.map((r) => <th key={r.technician} className="num">{short(r.technician)}</th>)}</tr></thead>
            <tbody>
              {data?.overview.map((w) => (
                <tr key={w.week} className={`cursor-pointer ${w.week === data.week ? "bg-accent-soft" : ""}`} onClick={() => setWeek(w.week)}>
                  <td>{date(w.week)}</td>
                  {w.rows.map((r) => (
                    <td key={r.technician} className="num">
                      <span className="inline-block min-w-14 rounded-sm px-1.5 py-0.5 text-xs font-medium"
                        style={{ background: r.sobrecarga ? "var(--danger-soft)" : `color-mix(in srgb, var(--chart-1) ${Math.round(Math.min(r.utilizacion, 1) * 45)}%, transparent)`, color: r.sobrecarga ? "var(--danger)" : "var(--text)" }}>
                        {r.sobrecarga && "⚠ "}{pct(r.utilizacion)}
                      </span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
