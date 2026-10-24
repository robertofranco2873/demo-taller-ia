import { ArrowLeft, ArrowRight, ClipboardList, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Field, SelectField } from "../components/fields";
import { ThemedLoader } from "../components/loaders";
import { Table } from "../components/Table";
import { Button, Card, ErrorState, InfoTip, Notice, PageHeader, StatusBadge, useToast } from "../components/ui";
import { api } from "../lib/api";
import { celebrateOrder } from "../lib/celebrate";
import { date, dateTime, hours, money, pct } from "../lib/format";
import { useApi } from "../lib/hooks";
import type { Bay, OrderRow, Technician, Timer } from "../lib/types";

interface Item { id: number; service_code: string; service_name: string; qty: number; std_hours: number; actual_hours: number | null; line_subtotal: number }
interface Detail {
  order: OrderRow & { started_at: string | null; finished_at: string | null; delivered_at: string | null; labor: number; parts: number; subtotal: number; iva: number; notes: string; margin_pct: number; labor_rate: number };
  items: Item[]; timer: Timer; next_status: string | null;
  variance: { diferencia_h: number; variacion_pct: number; eficiencia: number } | null;
}

/** Detalle de una orden. Se reutiliza dentro del modal del Pareto (nivel 3). */
export function OrderDetailBody({ id, onChanged }: { id: number; onChanged?: () => void }) {
  const toast = useToast();
  const { data, error, loading, reload } = useApi<Detail>(`/api/orders/${id}`);
  const techs = useApi<Technician[]>("/api/technicians");
  const bays = useApi<Bay[]>("/api/bays");
  const [assign, setAssign] = useState({ technician_id: 0, bay_id: 0, scheduled_date: "" });
  const [actual, setActual] = useState<Record<number, number>>({});
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!data) return;
    setAssign({ technician_id: data.order.technician_id, bay_id: data.order.bay_id, scheduled_date: data.order.scheduled_date });
    setActual(Object.fromEntries(data.items.map((i) => [i.id, Number((i.actual_hours ?? i.std_hours).toFixed(2))])));
  }, [data]);

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (loading || !data) return <ThemedLoader kind="lift" label="Subiendo la orden al elevador…" />;
  const o = data.order;
  const open = o.status !== "entregada";

  async function saveAssignment() {
    try {
      await api.patch(`/api/orders/${id}/assignment`, assign);
      toast("Asignación guardada.");
      reload();
      onChanged?.();
    } catch (e) {
      toast((e as Error).message, "danger");
    }
  }

  async function advance() {
    setBusy(true);
    try {
      await api.post(`/api/orders/${id}/advance`, { status: data!.next_status, actual_hours: data!.next_status === "terminada" ? actual : undefined });
      if (data!.next_status === "terminada") celebrateOrder();
      toast(`${o.folio}: ${data!.next_status}.`);
      reload();
      onChanged?.();
    } catch (e) {
      toast((e as Error).message, "danger");
    } finally {
      setBusy(false);
    }
  }

  const totalActual = Object.values(actual).reduce((a, b) => a + b, 0);
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-4">
        {[["Estado", <StatusBadge key="s" status={o.status} />], ["Cliente", o.customer], ["Vehículo", o.vehicle], ["Total", money(o.total)],
          ["Recepción", dateTime(o.created_at)], ["Compromiso", date(o.due_date)], ["Técnico", o.technician], ["Bahía", o.bay]].map(([l, v], i) => (
          <div key={i} className="rounded-md bg-surface-muted p-3"><div className="text-xs text-secondary">{l}</div><div className="mt-0.5 text-sm font-semibold text-text">{v}</div></div>
        ))}
      </div>

      <Table rows={data.items} rowKey={(i) => i.id} columns={[
        { key: "s", header: "Servicio", render: (i) => `${i.service_code} · ${i.service_name}` },
        { key: "q", header: "Cant.", numeric: true, render: (i) => i.qty },
        { key: "e", header: "Estándar", numeric: true, render: (i) => hours(i.std_hours) },
        { key: "r", header: "Real", numeric: true, render: (i) => hours(i.actual_hours) },
        { key: "m", header: "Importe", numeric: true, render: (i) => money(i.line_subtotal) },
      ]} />

      {data.variance && (
        <Notice kind={data.variance.eficiencia >= 1 ? "success" : "warning"}>
          Real {hours(o.actual_hours)} vs. estándar {hours(o.std_hours)} → variación {pct(data.variance.variacion_pct)}, eficiencia <b>{pct(data.variance.eficiencia)}</b>.
        </Notice>
      )}
      {data.timer.hours > 0 && !o.actual_hours && <Notice kind="info">Cronómetro del técnico: {hours(data.timer.hours)} {data.timer.running ? "(corriendo)" : "(pausado)"}.</Notice>}

      {open && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card title="Asignación">
            <div className="grid gap-3">
              <SelectField label="Técnico" value={assign.technician_id} onChange={(e) => setAssign({ ...assign, technician_id: Number(e.target.value) })}>
                {techs.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </SelectField>
              <SelectField label="Bahía" value={assign.bay_id} onChange={(e) => setAssign({ ...assign, bay_id: Number(e.target.value) })}>
                {bays.data?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </SelectField>
              <Field label="Fecha programada" type="date" value={assign.scheduled_date} onChange={(e) => setAssign({ ...assign, scheduled_date: e.target.value })} />
              <Button icon={Save} onClick={saveAssignment}>Guardar asignación</Button>
            </div>
          </Card>
          <Card title={<span className="inline-flex items-center gap-1">Cambiar estado<InfoTip text="Solo se avanza un paso. Para terminar se registra el tiempo real de cada servicio." /></span>}>
            <p className="mb-3 text-sm text-secondary">{o.status} <ArrowRight size={14} className="inline" aria-hidden /> <b className="text-text">{data.next_status}</b></p>
            {data.next_status === "terminada" && (
              <div className="mb-3 space-y-2">
                {data.items.map((i) => (
                  <Field key={i.id} label={`Horas reales · ${i.service_code}`} type="number" min={0.05} step={0.05} value={actual[i.id] ?? ""}
                    onChange={(e) => setActual({ ...actual, [i.id]: Number(e.target.value) })} />
                ))}
                <p className="text-xs text-muted">Total real {hours(totalActual)} · eficiencia {pct(totalActual ? o.std_hours / totalActual : null)}</p>
              </div>
            )}
            <Button variant="primary" icon={ArrowRight} loading={busy} onClick={advance} className="w-full">Pasar a «{data.next_status}»</Button>
          </Card>
        </div>
      )}
    </div>
  );
}

export default function OrdenDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data } = useApi<{ order: OrderRow }>(`/api/orders/${id}`);
  return (
    <div>
      <PageHeader icon={ClipboardList} title={data ? `Orden ${data.order.folio}` : "Orden"}
        crumbs={[{ label: "Órdenes", to: "/ordenes" }, { label: data?.order.folio ?? "…" }]}
        actions={<Button variant="ghost" icon={ArrowLeft} onClick={() => navigate(-1)}>Regresar</Button>} />
      <OrderDetailBody id={Number(id)} />
    </div>
  );
}
