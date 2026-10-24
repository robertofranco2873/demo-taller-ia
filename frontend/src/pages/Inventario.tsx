import { AlertTriangle, Boxes, PackagePlus, PackageX } from "lucide-react";
import { useState } from "react";
import { Field, SelectField } from "../components/fields";
import { Table } from "../components/Table";
import { Button, Card, ErrorState, InfoTip, Modal, PageHeader, Segmented, StatusBadge, useToast } from "../components/ui";
import { api } from "../lib/api";
import { dateTime, money, num, pct } from "../lib/format";
import { useApi } from "../lib/hooks";

interface Part {
  id: number; code: string; name: string; price: number; stock: number; lead_time_days: number; demanda_diaria: number;
  desv_diaria: number; stock_seguridad: number; punto_reorden: number; eoq: number; cobertura_dias: number | null; estado: "ok" | "reordenar" | "agotado";
}
interface Inv { rows: Part[]; service_level: number; window_days: number; formulas: Record<string, string> }
interface Movement { created_at: string; qty: number; kind: string; note: string; folio: string | null }

export default function Inventario() {
  const toast = useToast();
  const { data, error, loading, reload } = useApi<Inv>("/api/inventory");
  const [filter, setFilter] = useState<"todas" | "alerta">("todas");
  const [sel, setSel] = useState<Part | null>(null);
  const [mov, setMov] = useState({ kind: "entrada", qty: 0, note: "" });
  const [edit, setEdit] = useState({ price: 0, lead_time_days: 0 });
  const history = useApi<Movement[]>(sel ? `/api/inventory/${sel.id}/movements` : null);
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const rows = (data?.rows ?? []).filter((r) => filter === "todas" || r.estado !== "ok").sort((a, b) => (a.estado === "ok" ? 1 : 0) - (b.estado === "ok" ? 1 : 0));
  const alerts = data?.rows.filter((r) => r.estado !== "ok").length ?? 0;
  const open = (p: Part) => {
    setSel(p);
    setMov({ kind: "entrada", qty: Math.max(1, Math.ceil(p.eoq)), note: "" });
    setEdit({ price: p.price, lead_time_days: p.lead_time_days });
  };

  async function saveMovement() {
    try {
      await api.post(`/api/inventory/${sel!.id}/movements`, mov);
      await api.put(`/api/parts/${sel!.id}`, edit);
      toast("Inventario actualizado.");
      setSel(null);
      reload();
    } catch (e) {
      toast((e as Error).message, "danger");
    }
  }

  return (
    <div>
      <PageHeader icon={Boxes} title="Inventario de refacciones" subtitle={data ? `Demanda de los últimos ${data.window_days} días · nivel de servicio ${pct(data.service_level)}` : undefined}
        crumbs={[{ label: "Administración" }, { label: "Inventario" }]} />
      <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        {[["Refacciones", data?.rows.length, Boxes], ["Por reordenar", data?.rows.filter((r) => r.estado === "reordenar").length, AlertTriangle],
          ["Agotadas", data?.rows.filter((r) => r.estado === "agotado").length, PackageX],
          ["Valor del stock", data ? money(data.rows.reduce((s, r) => s + r.stock * r.price, 0)) : undefined, PackagePlus]].map(([l, v, Icon]) => {
          const I = Icon as typeof Boxes;
          return <Card key={l as string} hover padded={false} className="p-4"><I size={18} className="mb-1 text-accent" aria-hidden /><div className="text-xl font-bold text-text">{(v as string | number) ?? "…"}</div><div className="text-xs text-muted">{l as string}</div></Card>;
        })}
      </div>
      <Card title="Existencias" actions={<Segmented label="Filtro" value={filter} onChange={setFilter} options={[{ value: "todas", label: "Todas" }, { value: "alerta", label: `Alertas (${alerts})` }]} />}>
        <Table rows={rows} loading={loading} rowKey={(p) => p.id} onRowClick={open} maxHeight={640} columns={[
          { key: "e", header: "Estado", render: (p) => <StatusBadge status={p.estado} /> },
          { key: "n", header: "Refacción", render: (p) => <><span className="text-xs text-muted">{p.code}</span> {p.name}</> },
          { key: "s", header: "Stock", numeric: true, render: (p) => num(p.stock, 0) },
          { key: "d", header: <span className="inline-flex items-center gap-1">d̄/día<InfoTip text="Demanda diaria promedio (días sin consumo cuentan como 0)." /></span>, numeric: true, hideOnMobile: true, render: (p) => num(p.demanda_diaria, 2) },
          { key: "l", header: "L (días)", numeric: true, hideOnMobile: true, render: (p) => num(p.lead_time_days, 0) },
          { key: "ss", header: <span className="inline-flex items-center gap-1">SS<InfoTip text="Stock de seguridad" formula={data?.formulas.stock_seguridad} /></span>, numeric: true, hideOnMobile: true, render: (p) => num(p.stock_seguridad, 1) },
          { key: "r", header: <span className="inline-flex items-center gap-1">ROP<InfoTip text="Punto de reorden: pide cuando el stock llegue aquí." formula={data?.formulas.punto_reorden} /></span>, numeric: true, render: (p) => num(p.punto_reorden, 1) },
          { key: "q", header: <span className="inline-flex items-center gap-1">EOQ<InfoTip text="Lote económico de compra." formula={data?.formulas.eoq} /></span>, numeric: true, hideOnMobile: true, render: (p) => num(p.eoq, 0) },
          { key: "c", header: "Cobertura", numeric: true, render: (p) => (p.cobertura_dias == null ? "—" : `${num(p.cobertura_dias, 0)} d`) },
        ]} />
      </Card>

      <Modal open={!!sel} onClose={() => setSel(null)} title={sel?.name ?? ""} subtitle={sel ? `Stock ${num(sel.stock, 0)} · ROP ${num(sel.punto_reorden, 1)} · EOQ sugerido ${num(sel.eoq, 0)}` : ""}>
        {sel && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <SelectField label="Movimiento" value={mov.kind} onChange={(e) => setMov({ ...mov, kind: e.target.value })}>
                <option value="entrada">Entrada (compra)</option><option value="salida">Salida</option><option value="ajuste">Ajuste (+/−)</option>
              </SelectField>
              <Field label="Cantidad" type="number" value={mov.qty} onChange={(e) => setMov({ ...mov, qty: Number(e.target.value) })} />
              <Field label="Precio" type="number" min={0} value={edit.price} onChange={(e) => setEdit({ ...edit, price: Number(e.target.value) })} />
              <Field label="Tiempo de entrega (días)" type="number" min={0} value={edit.lead_time_days} onChange={(e) => setEdit({ ...edit, lead_time_days: Number(e.target.value) })} />
              <div className="col-span-2"><Field label="Nota" value={mov.note} onChange={(e) => setMov({ ...mov, note: e.target.value })} /></div>
            </div>
            <div className="flex justify-end gap-2"><Button variant="ghost" onClick={() => setSel(null)}>Cancelar</Button><Button variant="primary" disabled={!mov.qty} onClick={saveMovement}>Guardar</Button></div>
            <div>
              <h3 className="mb-1 text-sm font-semibold text-text">Últimos movimientos</h3>
              <Table rows={history.data} loading={history.loading} rowKey={(_, i) => i} maxHeight={220} columns={[
                { key: "d", header: "Fecha", render: (m) => dateTime(m.created_at) }, { key: "k", header: "Tipo", render: (m) => m.kind },
                { key: "q", header: "Cant.", numeric: true, render: (m) => num(m.qty, 0) }, { key: "o", header: "Orden / nota", render: (m) => m.folio ?? m.note },
              ]} />
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
