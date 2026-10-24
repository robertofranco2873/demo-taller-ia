import { Search, UserSquare2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table } from "../components/Table";
import { Card, ErrorState, Modal, PageHeader, StatusBadge } from "../components/ui";
import { date, money } from "../lib/format";
import { useApi, useDebounced } from "../lib/hooks";
import type { OrderRow } from "../lib/types";

interface Customer { customer: string; phone: string; ordenes: number; total: number; ultima_visita: string; vehiculos: string }

export default function Clientes() {
  const [q, setQ] = useState("");
  const dq = useDebounced(q);
  const navigate = useNavigate();
  const { data, error, loading, reload } = useApi<Customer[]>("/api/customers", { q: dq });
  const [sel, setSel] = useState<Customer | null>(null);
  const history = useApi<OrderRow[]>(sel ? "/api/customers/orders" : null, sel ? { customer: sel.customer, phone: sel.phone ?? "" } : undefined);

  return (
    <div>
      <PageHeader icon={UserSquare2} title="Clientes" subtitle="Derivados de las órdenes (todos ficticios)" crumbs={[{ label: "Operación" }, { label: "Clientes" }]} />
      <Card>
        <div className="relative mb-4 max-w-md">
          <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
          <input className="field pl-9" placeholder="Nombre, teléfono o vehículo…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Buscar cliente" />
        </div>
        {error ? <ErrorState message={error} onRetry={reload} /> : (
          <Table rows={data} loading={loading} rowKey={(c) => `${c.customer}-${c.phone}`} onRowClick={setSel} maxHeight={620}
            columns={[
              { key: "n", header: "Cliente", render: (c) => <span className="font-medium text-text">{c.customer}</span> },
              { key: "p", header: "Teléfono", hideOnMobile: true, render: (c) => c.phone },
              { key: "v", header: "Vehículos", hideOnMobile: true, render: (c) => c.vehiculos },
              { key: "o", header: "Órdenes", numeric: true, render: (c) => c.ordenes },
              { key: "t", header: "Total", numeric: true, render: (c) => money(c.total) },
              { key: "u", header: "Última visita", render: (c) => date(c.ultima_visita) },
            ]} />
        )}
      </Card>
      <Modal open={!!sel} onClose={() => setSel(null)} title={sel?.customer ?? ""} subtitle={`${sel?.phone} · ${sel?.vehiculos}`} wide>
        <Table rows={history.data} loading={history.loading} rowKey={(o) => o.id} onRowClick={(o) => navigate(`/ordenes/${o.id}`)}
          columns={[
            { key: "f", header: "Folio", render: (o) => o.folio },
            { key: "s", header: "Estado", render: (o) => <StatusBadge status={o.status} /> },
            { key: "d", header: "Recepción", render: (o) => date(o.created_at) },
            { key: "v", header: "Vehículo", render: (o) => o.vehicle },
            { key: "t", header: "Total", numeric: true, render: (o) => money(o.total) },
          ]} />
      </Modal>
    </div>
  );
}
