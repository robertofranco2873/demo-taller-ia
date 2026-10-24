import { ClipboardList, Plus, Search } from "lucide-react";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { NewOrderModal } from "../components/NewOrderModal";
import { Table } from "../components/Table";
import { Button, Card, ErrorState, PageHeader, Segmented, StatusBadge } from "../components/ui";
import { date, money } from "../lib/format";
import { useApi, useDebounced } from "../lib/hooks";
import type { OrderRow } from "../lib/types";

type Filter = "abiertas" | "recibida" | "en proceso" | "terminada" | "entregada" | "vencidas";
const STATUS_PARAM: Record<Filter, string> = {
  abiertas: "recibida,en proceso,terminada", recibida: "recibida", "en proceso": "en proceso",
  terminada: "terminada", entregada: "entregada", vencidas: "recibida,en proceso",
};

export default function Ordenes() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const initial = (params.get("filtro") === "vencidas" ? "vencidas" : (params.get("estado") as Filter)) || "abiertas";
  const [filter, setFilter] = useState<Filter>(initial in STATUS_PARAM ? initial : "abiertas");
  const [q, setQ] = useState(params.get("q") ?? "");
  const [newOpen, setNewOpen] = useState(false);
  const dq = useDebounced(q);
  const { data, error, loading, reload } = useApi<OrderRow[]>("/api/orders", {
    status: STATUS_PARAM[filter], q: dq, technician_id: params.get("tecnico"), limit: 300,
  });
  const rows = filter === "vencidas" ? data?.filter((o) => o.vencida) : data;

  return (
    <div>
      <PageHeader icon={ClipboardList} title="Órdenes de trabajo" subtitle="recibida → en proceso → terminada → entregada"
        crumbs={[{ label: "Operación" }, { label: "Órdenes" }]}
        actions={<Button variant="primary" icon={Plus} onClick={() => setNewOpen(true)}>Nueva orden</Button>} />
      <Card>
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <div className="overflow-x-auto">
            <Segmented label="Estado" value={filter} onChange={(v) => { setFilter(v); setParams({}); }} options={[
              { value: "abiertas", label: "Abiertas" }, { value: "recibida", label: "Recibidas" }, { value: "en proceso", label: "En proceso" },
              { value: "terminada", label: "Terminadas" }, { value: "entregada", label: "Entregadas" }, { value: "vencidas", label: "Vencidas" },
            ]} />
          </div>
          <div className="relative min-w-52 flex-1">
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
            <input className="field pl-9" placeholder="Folio, cliente o vehículo…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Buscar orden" />
          </div>
        </div>
        {error ? <ErrorState message={error} onRetry={reload} /> : (
          <Table rows={rows} loading={loading} rowKey={(o) => o.id} onRowClick={(o) => navigate(`/ordenes/${o.id}`)} maxHeight={620}
            columns={[
              { key: "f", header: "Folio", render: (o) => <span className="font-semibold text-text">{o.folio}</span> },
              { key: "s", header: "Estado", render: (o) => <span className="flex flex-wrap gap-1"><StatusBadge status={o.status} />{o.vencida && <StatusBadge status="vencida" />}</span> },
              { key: "c", header: "Cliente", render: (o) => o.customer },
              { key: "v", header: "Vehículo", hideOnMobile: true, render: (o) => o.vehicle },
              { key: "t", header: "Técnico", hideOnMobile: true, render: (o) => o.technician },
              { key: "b", header: "Bahía", hideOnMobile: true, render: (o) => o.bay },
              { key: "d", header: "Compromiso", render: (o) => date(o.due_date) },
              { key: "m", header: "Total", numeric: true, render: (o) => money(o.total) },
            ]} />
        )}
      </Card>
      <NewOrderModal open={newOpen} onClose={() => { setNewOpen(false); reload(); }} />
    </div>
  );
}
