import { ArrowLeft, BarChart3, ListOrdered } from "lucide-react";
import { useState } from "react";
import { Chart } from "../components/Chart";
import { DateRange } from "../components/fields";
import { ThemedLoader } from "../components/loaders";
import { Table } from "../components/Table";
import { Button, Card, ErrorState, Modal, Notice, PageHeader, Segmented, StatusBadge, type Crumb } from "../components/ui";
import { useChartColors } from "../lib/chartTheme";
import { barOption, controlOption, paretoOption } from "../lib/charts";
import { date, hours, money, moneyShort, month, pct } from "../lib/format";
import { useApi } from "../lib/hooks";
import { OrderDetailBody } from "./OrdenDetalle";

interface ParetoRow { service_name: string; service_id: number; valor: number; pct: number; pct_acumulado: number; clase: "A" | "B" }
interface ParetoData { rows: ParetoRow[]; vital_few: number; total: number; share: number; range: { start: string; end: string } }
interface ServiceLevel {
  service: { id: number; code: string; name: string; std_hours: number };
  mensual: { mes: string; veces: number; ingreso: number }[];
  tecnicos: { technician: string; veces: number; real_promedio_h: number; estandar_h: number; eficiencia: number }[];
  veces: number; ingreso: number; real_promedio_h: number | null; estandar_h: number | null;
  control: { points: { valor: number; fuera_de_limites: boolean; racha: boolean; folio: string; technician: string }[]; limits: { lc: number; lsc: number; lic: number } } | null;
}
interface OrderLevel { order_id: number; folio: string; status: string; customer: string; vehicle: string; technician: string; created_at: string; qty: number; std_hours: number; actual_hours: number | null; line_subtotal: number }

type By = "ingreso" | "frecuencia";

export default function Pareto() {
  const c = useChartColors();
  const [by, setBy] = useState<By>("ingreso");
  const [range, setRange] = useState<{ start: string; end: string } | null>(null);
  const [service, setService] = useState<{ id: number; name: string } | null>(null);
  const [showOrders, setShowOrders] = useState(false);
  const [order, setOrder] = useState<number | null>(null);
  const dash = useApi<{ range: { min: string; max: string; start: string; end: string } }>("/api/dashboard");
  const lvl1 = useApi<ParetoData>("/api/pareto", { by, ...(range ?? {}) });
  const lvl2 = useApi<ServiceLevel>(service ? `/api/pareto/service/${service.id}` : null, range ?? undefined);
  const lvl3 = useApi<OrderLevel[]>(service && showOrders ? `/api/pareto/service/${service.id}/orders` : null, range ?? undefined);
  const r = range ?? (dash.data ? { start: dash.data.range.start, end: dash.data.range.end } : null);

  const crumbs: Crumb[] = [
    { label: "Análisis" },
    service ? { label: "Pareto", onClick: () => { setService(null); setShowOrders(false); } } : { label: "Pareto" },
  ];
  if (service) crumbs.push(showOrders ? { label: service.name, onClick: () => setShowOrders(false) } : { label: service.name });
  if (service && showOrders) crumbs.push({ label: "Órdenes" });
  const back = () => (showOrders ? setShowOrders(false) : setService(null));

  return (
    <div>
      <PageHeader icon={BarChart3} title="Análisis de Pareto (80/20)" subtitle="Clic en una barra para profundizar" crumbs={crumbs}
        actions={<>
          {service && <Button variant="ghost" icon={ArrowLeft} onClick={back}>Regresar</Button>}
          {dash.data && r && <DateRange start={r.start} end={r.end} min={dash.data.range.min} max={dash.data.range.max} onChange={(start, end) => setRange({ start, end })} />}
        </>} />

      {!service && (
        <Card actions={<Segmented label="Criterio" value={by} onChange={setBy} options={[{ value: "ingreso", label: "Por ingreso" }, { value: "frecuencia", label: "Por frecuencia" }]} />}
          title="Nivel 1 · Servicios">
          {lvl1.error ? <ErrorState message={lvl1.error} onRetry={lvl1.reload} /> : (
            <>
              {lvl1.data && (
                <Notice kind="success">
                  <b>{lvl1.data.vital_few} de {lvl1.data.total} servicios ({pct(lvl1.data.vital_few / lvl1.data.total)})</b> concentran el <b>{pct(lvl1.data.share)}</b> del {by === "ingreso" ? "ingreso (sin IVA)" : "número de servicios realizados"}.
                </Notice>
              )}
              <Chart height={460} loading={lvl1.loading} ariaLabel="Pareto de servicios" onClick={(p) => {
                const row = lvl1.data?.rows[p.dataIndex];
                if (row) setService({ id: row.service_id, name: row.service_name });
              }} option={paretoOption(c, (lvl1.data?.rows ?? []).map((x) => ({
                name: x.service_name, pct: x.pct, cum: x.pct_acumulado, classA: x.clase === "A",
                value: by === "ingreso" ? `Ingreso: ${money(x.valor)}` : `Veces: ${x.valor}`,
              })))} />
              <p className="mt-2 text-xs text-muted">Barras oscuras = clase A (los «pocos vitales» hasta el 80 % acumulado). Barras y línea comparten el mismo eje en %.</p>
              <details className="mt-3">
                <summary className="cursor-pointer text-sm font-medium text-link">Ver como tabla</summary>
                <div className="mt-2">
                  <Table rows={lvl1.data?.rows} rowKey={(x) => x.service_id} maxHeight={360} onRowClick={(x) => setService({ id: x.service_id, name: x.service_name })} columns={[
                    { key: "n", header: "Servicio", render: (x) => x.service_name },
                    { key: "v", header: by === "ingreso" ? "Ingreso" : "Veces", numeric: true, render: (x) => (by === "ingreso" ? money(x.valor) : x.valor) },
                    { key: "p", header: "%", numeric: true, render: (x) => pct(x.pct, 1) },
                    { key: "a", header: "% acum.", numeric: true, render: (x) => pct(x.pct_acumulado, 1) },
                    { key: "c", header: "Clase", render: (x) => x.clase },
                  ]} />
                </div>
              </details>
            </>
          )}
        </Card>
      )}

      {service && !showOrders && (
        lvl2.loading || !lvl2.data ? <ThemedLoader kind="gear" label="Profundizando en el servicio…" /> : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {[["Veces realizado", String(lvl2.data.veces)], ["Ingreso (sin IVA)", money(lvl2.data.ingreso)],
                ["Real promedio", hours(lvl2.data.real_promedio_h)], ["Tiempo estándar", hours(lvl2.data.service.std_hours)]].map(([l, v]) => (
                <Card key={l} hover padded={false} className="p-4"><div className="text-xs text-secondary">{l}</div><div className="text-xl font-bold text-text">{v}</div></Card>
              ))}
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <Card title="Ocurrencias por mes">
                <Chart height={240} ariaLabel="Ocurrencias por mes" option={barOption(c, { categories: lvl2.data.mensual.map((m) => month(m.mes)), values: lvl2.data.mensual.map((m) => m.veces), name: "Veces", format: (v) => String(Math.round(v)), labels: true })} />
              </Card>
              <Card title="Ingreso por mes">
                <Chart height={240} ariaLabel="Ingreso por mes" option={barOption(c, { categories: lvl2.data.mensual.map((m) => month(m.mes)), values: lvl2.data.mensual.map((m) => m.ingreso), name: "Ingreso", format: moneyShort, labels: true, colors: lvl2.data.mensual.map(() => c.series[2]) })} />
              </Card>
              <Card title="Técnicos que lo realizan · real vs. estándar">
                <Table rows={lvl2.data.tecnicos} rowKey={(t) => t.technician} columns={[
                  { key: "t", header: "Técnico", render: (t) => t.technician },
                  { key: "v", header: "Veces", numeric: true, render: (t) => t.veces },
                  { key: "r", header: "Real prom.", numeric: true, render: (t) => hours(t.real_promedio_h) },
                  { key: "s", header: "Estándar", numeric: true, render: (t) => hours(t.estandar_h) },
                  { key: "e", header: "Eficiencia", numeric: true, render: (t) => <span className={t.eficiencia >= 1 ? "text-success" : "text-warning"}>{pct(t.eficiencia)}</span> },
                ]} />
              </Card>
              <Card title="Gráfica de control (tiempos reales)">
                {lvl2.data.control ? (
                  <Chart height={260} ariaLabel="Gráfica de control del servicio" option={controlOption(c, {
                    values: lvl2.data.control.points.map((p) => p.valor), signals: lvl2.data.control.points.map((p) => p.fuera_de_limites || p.racha),
                    labels: lvl2.data.control.points.map((p) => `${p.folio} · ${p.technician}`), limits: lvl2.data.control.limits, name: "Horas reales",
                  })} />
                ) : <p className="text-sm text-muted">Pocos datos para la gráfica de control.</p>}
              </Card>
            </div>
            <Button variant="primary" icon={ListOrdered} onClick={() => setShowOrders(true)}>Ver órdenes de este servicio</Button>
          </div>
        )
      )}

      {service && showOrders && (
        <Card title={`Nivel 3 · Órdenes de «${service.name}»`} actions={<span className="text-xs text-muted">Clic en una orden para ver su detalle</span>}>
          <Table rows={lvl3.data} loading={lvl3.loading} rowKey={(o) => `${o.order_id}`} onRowClick={(o) => setOrder(o.order_id)} maxHeight={600} columns={[
            { key: "f", header: "Folio", render: (o) => <span className="font-semibold">{o.folio}</span> },
            { key: "s", header: "Estado", render: (o) => <StatusBadge status={o.status} /> },
            { key: "d", header: "Recepción", render: (o) => date(o.created_at) },
            { key: "c", header: "Cliente", hideOnMobile: true, render: (o) => o.customer },
            { key: "t", header: "Técnico", hideOnMobile: true, render: (o) => o.technician },
            { key: "e", header: "Estándar", numeric: true, render: (o) => hours(o.std_hours) },
            { key: "r", header: "Real", numeric: true, render: (o) => hours(o.actual_hours) },
            { key: "i", header: "Importe", numeric: true, render: (o) => money(o.line_subtotal) },
          ]} />
        </Card>
      )}

      <Modal open={order !== null} onClose={() => setOrder(null)} wide title="Detalle de la orden">
        {order !== null && <OrderDetailBody id={order} />}
      </Modal>
    </div>
  );
}
