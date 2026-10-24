import { Bot, CalendarRange, Clock, DollarSign, Gauge, Layers, Receipt, Warehouse } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Chart } from "../components/Chart";
import { DateRange } from "../components/fields";
import { KpiCard } from "../components/KpiCard";
import { ThemedLoader } from "../components/loaders";
import { SkeletonCards } from "../components/Skeleton";
import { Table } from "../components/Table";
import { Button, Card, ErrorState, Modal, Notice, PageHeader, StatusBadge, useToast } from "../components/ui";
import { api } from "../lib/api";
import { celebrateGoalOnce } from "../lib/celebrate";
import { useChartColors } from "../lib/chartTheme";
import { barOption, trendOption } from "../lib/charts";
import { date, money, moneyShort, month, num, pct } from "../lib/format";
import { useApi } from "../lib/hooks";

type KpiKey = "ingresos" | "ticket" | "lead_time" | "eficiencia" | "utilizacion" | "backlog";
interface Def { nombre: string; formula: string; explicacion: string }
interface Dash {
  range: { start: string; end: string; min: string; max: string };
  kpis: Record<KpiKey, number | null> & { backlog_horas: number };
  definitions: Record<KpiKey, Def>;
  efficiency_goal: number;
  monthly: { mes: string; ingresos: number; ordenes: number; ticket: number; eficiencia: number | null }[];
  efficiency: { technician: string; technician_id: number; eficiencia: number; std_hours: number; actual_hours: number }[];
  bays: { bay: string; utilizacion: number; horas_usadas: number; horas_disponibles: number }[];
  backlog: { id: number; folio: string; status: string; technician: string; due_date: string; std_hours: number }[];
}

const FORMAT: Record<KpiKey, (v: number) => string> = {
  ingresos: moneyShort, ticket: money, lead_time: (v) => `${num(v, 1)} días`, eficiencia: (v) => pct(v),
  utilizacion: (v) => pct(v), backlog: (v) => `${Math.round(v)} órdenes`,
};

function KpiModal({ k, range, onClose }: { k: KpiKey | null; range: { start: string; end: string }; onClose: () => void }) {
  const c = useChartColors();
  const { data, loading } = useApi<Def & { valor: number | null; partes: Record<string, number>; tendencia: { mes: string; valor: number | null }[]; nota_tendencia: string | null }>(
    k ? `/api/dashboard/kpi/${k}` : null, range);
  return (
    <Modal open={k !== null} onClose={onClose} title={data?.nombre ?? "KPI"} subtitle={data?.explicacion}>
      {loading || !data || !k ? <ThemedLoader kind="piston" label="Calculando…" /> : (
        <div className="space-y-4">
          <div className="rounded-md bg-accent-soft p-4">
            <div className="text-xs text-secondary">Fórmula</div>
            <div className="font-mono text-sm text-accent">{data.formula}</div>
            <div className="mt-2 text-3xl font-bold text-text">{data.valor == null ? "—" : FORMAT[k](data.valor)}</div>
          </div>
          <div>
            <h3 className="mb-1 text-sm font-semibold text-text">Cómo se calculó</h3>
            <ul className="space-y-1 text-sm">
              {Object.entries(data.partes).map(([l, v]) => (
                <li key={l} className="flex justify-between border-b border-border py-1"><span className="text-secondary">{l}</span><span className="tabular-nums">{typeof v === "number" && v > 999 ? money(v) : num(v, v % 1 ? 1 : 0)}</span></li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="mb-1 text-sm font-semibold text-text">Tendencia mensual {data.nota_tendencia && <span className="font-normal text-muted">({data.nota_tendencia})</span>}</h3>
            <Chart height={220} ariaLabel={`Tendencia de ${data.nombre}`} option={trendOption(c, {
              categories: data.tendencia.map((t) => month(t.mes)), values: data.tendencia.map((t) => t.valor), name: data.nombre,
              format: k === "backlog" ? (v) => String(Math.round(v)) : k === "ingresos" ? moneyShort : FORMAT[k], area: true,
            })} />
          </div>
        </div>
      )}
    </Modal>
  );
}

interface MonthDetail {
  mes: string; mes_anterior: string | null;
  ordenes: { id: number; folio: string; status: string; customer: string; technician: string; total: number; created_at: string }[];
  ingresos_por_servicio: { service_name: string; ingreso: number; veces: number }[];
  comparativo: { kpi: string; nombre: string; actual: number | null; anterior: number | null; variacion: number | null }[];
  tecnicos: { technician: string; ordenes: number; ingresos: number; eficiencia: number | null }[];
}

function MonthModal({ mes, onClose }: { mes: string | null; onClose: () => void }) {
  const c = useChartColors();
  const { data, loading } = useApi<MonthDetail>(mes ? `/api/dashboard/month/${mes}` : null);
  const fmt = (kpi: string, v: number | null) => v == null ? "—" : kpi === "ingresos" || kpi === "ticket" ? money(v) : kpi === "eficiencia" ? pct(v) : kpi === "lead_time" ? `${num(v)} d` : String(Math.round(v));
  const top = data?.ingresos_por_servicio.slice(0, 8) ?? [];
  return (
    <Modal open={mes !== null} onClose={onClose} wide title={mes ? `Detalle de ${month(mes)}` : ""} subtitle={data?.mes_anterior ? `Comparado contra ${month(data.mes_anterior)}` : undefined}>
      {loading || !data ? <ThemedLoader kind="gear" label="Abriendo el mes…" /> : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            {data.comparativo.map((k) => (
              <div key={k.kpi} className="rounded-md bg-surface-muted p-3">
                <div className="text-xs text-secondary">{k.nombre}</div>
                <div className="text-base font-bold text-text">{fmt(k.kpi, k.actual)}</div>
                {k.variacion != null && (
                  <div className={`text-xs font-medium ${(k.kpi === "lead_time" ? -k.variacion : k.variacion) >= 0 ? "text-success" : "text-danger"}`}>
                    {k.variacion >= 0 ? "▲" : "▼"} {pct(Math.abs(k.variacion), 1)} vs. anterior
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <h3 className="mb-1 text-sm font-semibold text-text">Ingresos por servicio (sin IVA)</h3>
              <Chart height={280} ariaLabel="Ingresos por servicio del mes" option={barOption(c, {
                categories: top.map((s) => s.service_name), values: top.map((s) => s.ingreso), name: "Ingreso", format: moneyShort, horizontal: true, labels: true,
              })} />
            </div>
            <div>
              <h3 className="mb-1 text-sm font-semibold text-text">Técnicos destacados</h3>
              <Table rows={data.tecnicos} rowKey={(t) => t.technician} columns={[
                { key: "t", header: "Técnico", render: (t) => t.technician },
                { key: "o", header: "Órdenes", numeric: true, render: (t) => t.ordenes },
                { key: "i", header: "Ingresos", numeric: true, render: (t) => moneyShort(t.ingresos) },
                { key: "e", header: "Eficiencia", numeric: true, render: (t) => pct(t.eficiencia) },
              ]} />
            </div>
          </div>
          <div>
            <h3 className="mb-1 text-sm font-semibold text-text">Órdenes del mes ({data.ordenes.length})</h3>
            <Table rows={data.ordenes} rowKey={(o) => o.id} maxHeight={260} columns={[
              { key: "f", header: "Folio", render: (o) => o.folio },
              { key: "s", header: "Estado", render: (o) => <StatusBadge status={o.status} /> },
              { key: "c", header: "Cliente", render: (o) => o.customer },
              { key: "t", header: "Técnico", hideOnMobile: true, render: (o) => o.technician },
              { key: "m", header: "Total", numeric: true, render: (o) => money(o.total) },
            ]} />
          </div>
        </div>
      )}
    </Modal>
  );
}

interface TechDetail {
  technician: string; eficiencia: number | null; utilizacion: number; horas_reales: number; horas_disponibles: number;
  ordenes_cerradas: number; ordenes_pendientes: number; tendencia: { mes: string; eficiencia: number }[];
  servicios_frecuentes: { service_name: string; veces: number }[]; meta: number;
}

function TechModal({ id, range, onClose }: { id: number | null; range: { start: string; end: string }; onClose: () => void }) {
  const c = useChartColors();
  const { data, loading } = useApi<TechDetail>(id ? `/api/dashboard/technician/${id}` : null, range);
  return (
    <Modal open={id !== null} onClose={onClose} wide title={data?.technician ?? "Técnico"} subtitle="Eficiencia, utilización, órdenes, tendencia y servicios">
      {loading || !data ? <ThemedLoader kind="wrench" label="Consultando al técnico…" /> : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {[["Eficiencia", pct(data.eficiencia)], ["Utilización", pct(data.utilizacion)], ["Órdenes cerradas", String(data.ordenes_cerradas)], ["Pendientes", String(data.ordenes_pendientes)]].map(([l, v]) => (
              <div key={l} className="rounded-md bg-surface-muted p-3"><div className="text-xs text-secondary">{l}</div><div className="text-xl font-bold text-text">{v}</div></div>
            ))}
          </div>
          <p className="text-xs text-muted">Utilización = {num(data.horas_reales, 0)} h reales ÷ {num(data.horas_disponibles, 0)} h disponibles.</p>
          <div className="grid gap-4 md:grid-cols-2">
            <Chart height={240} ariaLabel="Tendencia de eficiencia" option={trendOption(c, {
              categories: data.tendencia.map((t) => month(t.mes)), values: data.tendencia.map((t) => t.eficiencia), name: "Eficiencia",
              format: (v) => pct(v), goal: { value: data.meta, label: `Meta ${pct(data.meta)}` }, area: true,
            })} />
            <Chart height={240} ariaLabel="Servicios más frecuentes" option={barOption(c, {
              categories: data.servicios_frecuentes.map((s) => s.service_name), values: data.servicios_frecuentes.map((s) => s.veces),
              name: "Veces", format: (v) => String(Math.round(v)), horizontal: true, labels: true,
            })} />
          </div>
        </div>
      )}
    </Modal>
  );
}

export default function Dashboard() {
  const c = useChartColors();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const [range, setRange] = useState<{ start: string; end: string } | null>(null);
  const { data, error, loading, reload } = useApi<Dash>("/api/dashboard", range ?? undefined);
  const [kpi, setKpi] = useState<KpiKey | null>(null);
  const [mes, setMes] = useState<string | null>(null);
  const tech = params.get("tecnico") ? Number(params.get("tecnico")) : null;
  const ai = useApi<{ enabled: boolean }>("/api/ai/status");
  const [summary, setSummary] = useState<string | null>(null);
  const [aiBusy, setAiBusy] = useState(false);

  useEffect(() => {
    if (data && !range) setRange({ start: data.range.start, end: data.range.end });
  }, [data, range]);

  const goal = data?.efficiency_goal ?? 1;
  const reached = !!data?.kpis.eficiencia && data.kpis.eficiencia >= goal;
  useEffect(() => {
    if (reached) celebrateGoalOnce("taller");
  }, [reached]);

  if (error) return <ErrorState message={error} onRetry={reload} />;
  const r = range ?? data?.range;

  async function aiSummary() {
    setAiBusy(true);
    try {
      setSummary((await api.post<{ text: string }>("/api/ai/summary", r)).text);
    } catch (e) {
      toast((e as Error).message, "danger");
    } finally {
      setAiBusy(false);
    }
  }

  const cards: { k: KpiKey; icon: typeof Gauge; accent: "purple" | "blue" | "gold"; sub?: string }[] = [
    { k: "ingresos", icon: DollarSign, accent: "gold" },
    { k: "ticket", icon: Receipt, accent: "purple" },
    { k: "eficiencia", icon: Gauge, accent: "blue", sub: `Meta ${pct(goal)}${reached ? " · ¡alcanzada! 🏆" : ""}` },
    { k: "utilizacion", icon: Warehouse, accent: "purple" },
    { k: "lead_time", icon: Clock, accent: "gold" },
    { k: "backlog", icon: Layers, accent: "blue", sub: data ? `${num(data.kpis.backlog_horas, 0)} h estándar pendientes` : undefined },
  ];

  return (
    <div>
      <PageHeader icon={Gauge} title="Dashboard de indicadores" subtitle="Clic en un KPI, un mes o un técnico para ver el detalle"
        crumbs={[{ label: "Análisis" }, { label: "Dashboard" }]}
        actions={data && r && <DateRange start={r.start} end={r.end} min={data.range.min} max={data.range.max} onChange={(start, end) => setRange({ start, end })} />} />

      {!data || loading ? <SkeletonCards n={6} /> : (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
          {cards.map(({ k, icon, accent, sub }) => (
            <KpiCard key={k} label={data.definitions[k].nombre} value={data.kpis[k]} format={FORMAT[k]} icon={icon} accent={accent}
              hint={data.definitions[k].explicacion} formula={data.definitions[k].formula} sub={sub ?? "Clic para ver fórmula y tendencia"} onClick={() => setKpi(k)} />
          ))}
        </div>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title={<span className="inline-flex items-center gap-2"><CalendarRange size={16} className="text-accent" aria-hidden />Ingresos por mes</span>} actions={<span className="text-xs text-muted">Clic en un mes</span>}>
          <Chart loading={!data} ariaLabel="Ingresos por mes" onClick={(p) => data && setMes(data.monthly[p.dataIndex].mes)} option={barOption(c, {
            categories: (data?.monthly ?? []).map((m) => month(m.mes)), values: (data?.monthly ?? []).map((m) => m.ingresos), name: "Ingresos", format: moneyShort, labels: true,
          })} />
        </Card>
        <Card title="Eficiencia por técnico" actions={<span className="text-xs text-muted">Clic en un técnico</span>}>
          <Chart loading={!data} ariaLabel="Eficiencia por técnico" onClick={(p) => data && setParams({ tecnico: String(data.efficiency[p.dataIndex].technician_id) })} option={barOption(c, {
            categories: (data?.efficiency ?? []).map((e) => e.technician.split("·")[1]?.trim() ?? e.technician),
            values: (data?.efficiency ?? []).map((e) => e.eficiencia), name: "Eficiencia", format: (v) => pct(v), labels: true,
            colors: (data?.efficiency ?? []).map((e) => (e.eficiencia >= goal ? c.series[0] : c.series[1])), refLine: { value: goal, label: `Meta ${pct(goal)}` },
          })} />
        </Card>
        <Card title="Utilización de bahías">
          <Chart loading={!data} height={260} ariaLabel="Utilización de bahías" option={barOption(c, {
            categories: (data?.bays ?? []).map((b) => b.bay), values: (data?.bays ?? []).map((b) => b.utilizacion), name: "Utilización", format: (v) => pct(v), labels: true,
          })} />
        </Card>
        <Card title={`Órdenes pendientes (${data?.backlog.length ?? "…"})`}>
          <Table rows={data?.backlog} loading={!data} rowKey={(o) => o.id} maxHeight={260} columns={[
            { key: "f", header: "Folio", render: (o) => o.folio },
            { key: "s", header: "Estado", render: (o) => <StatusBadge status={o.status} /> },
            { key: "t", header: "Técnico", render: (o) => o.technician.split("·")[1]?.trim() ?? o.technician },
            { key: "d", header: "Compromiso", render: (o) => date(o.due_date) },
            { key: "h", header: "Horas", numeric: true, render: (o) => num(o.std_hours, 2) },
          ]} />
        </Card>
      </div>

      <Card className="mt-4" title={<span className="inline-flex items-center gap-2"><Bot size={18} className="text-accent" aria-hidden />Resumen ejecutivo (IA)</span>}>
        {ai.data?.enabled ? (
          <>
            <p className="mb-3 text-sm text-secondary">La IA recibe solo los KPIs ya calculados de este periodo y los explica en lenguaje claro.</p>
            <Button variant="primary" icon={Bot} loading={aiBusy} onClick={aiSummary}>Generar resumen</Button>
            {summary && <div className="mt-4 whitespace-pre-wrap rounded-md bg-surface-muted p-4 text-sm leading-relaxed text-text">{summary.replace(/\*\*/g, "")}</div>}
          </>
        ) : <Notice kind="info">IA desactivada (sin <code>GROQ_API_KEY</code>). Todos los indicadores funcionan sin ella.</Notice>}
      </Card>

      {r && <KpiModal k={kpi} range={r} onClose={() => setKpi(null)} />}
      <MonthModal mes={mes} onClose={() => setMes(null)} />
      {r && <TechModal id={tech} range={r} onClose={() => setParams({})} />}
    </div>
  );
}
