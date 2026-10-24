import { ClipboardPlus } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { isoDate } from "../lib/format";
import { useApi } from "../lib/hooks";
import type { Bay, Service, Technician } from "../lib/types";
import { Field, SelectField } from "./fields";
import { Button, Modal, Notice, useToast } from "./ui";

export interface OrderDraft {
  customer: string;
  phone: string;
  vehicle: string;
  items: { service_id: number; qty: number }[];
}

function addWorkdays(n: number) {
  const d = new Date();
  while (n > 0) {
    d.setDate(d.getDate() + 1);
    if (d.getDay() !== 0) n--;
  }
  return isoDate(d);
}

/** Crear orden de trabajo; el precio lo calcula el backend con la fórmula. */
export function NewOrderModal({ open, onClose, draft }: { open: boolean; onClose: () => void; draft?: OrderDraft }) {
  const toast = useToast();
  const navigate = useNavigate();
  const techs = useApi<Technician[]>(open ? "/api/technicians" : null);
  const bays = useApi<Bay[]>(open ? "/api/bays" : null);
  const services = useApi<Service[]>(open && !draft ? "/api/services" : null);
  const [form, setForm] = useState({ customer: "", phone: "", vehicle: "", technician_id: 1, bay_id: 1, scheduled_date: isoDate(new Date()), due_date: addWorkdays(2), notes: "" });
  const [items, setItems] = useState<{ service_id: number; qty: number }[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setError(null);
    setForm((f) => ({ ...f, customer: draft?.customer ?? "", phone: draft?.phone ?? "", vehicle: draft?.vehicle ?? "" }));
    setItems(draft?.items ?? []);
  }, [open, draft]);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const { folio } = await api.post<{ folio: string }>("/api/orders", { ...form, items });
      toast(`Orden ${folio} creada.`);
      onClose();
      navigate(`/ordenes?q=${folio}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Nueva orden de trabajo" subtitle="El precio se calcula con la fórmula del cotizador">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Cliente *" value={form.customer} onChange={(e) => setForm({ ...form, customer: e.target.value })} />
        <Field label="Teléfono" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        <div className="sm:col-span-2"><Field label="Vehículo" value={form.vehicle} onChange={(e) => setForm({ ...form, vehicle: e.target.value })} /></div>
        {!draft && (
          <div className="sm:col-span-2">
            <SelectField label="Agregar servicio" value="" onChange={(e) => {
              const sid = Number(e.target.value);
              if (sid && !items.some((i) => i.service_id === sid)) setItems([...items, { service_id: sid, qty: 1 }]);
            }}>
              <option value="">Elige un servicio…</option>
              {services.data?.map((s) => <option key={s.id} value={s.id}>{s.code} · {s.name}</option>)}
            </SelectField>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {items.map((i) => {
                const s = services.data?.find((x) => x.id === i.service_id);
                return (
                  <button key={i.service_id} type="button" onClick={() => setItems(items.filter((x) => x.service_id !== i.service_id))}
                    className="cursor-pointer rounded-full bg-accent-soft px-2.5 py-1 text-xs text-accent hover:line-through" aria-label={`Quitar ${s?.name}`}>
                    {s?.code} · {s?.name} ✕
                  </button>
                );
              })}
            </div>
          </div>
        )}
        {draft && <div className="sm:col-span-2"><Notice kind="info">{draft.items.length} servicio(s) de la cotización.</Notice></div>}
        <SelectField label="Técnico" value={form.technician_id} onChange={(e) => setForm({ ...form, technician_id: Number(e.target.value) })}>
          {techs.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </SelectField>
        <SelectField label="Bahía" value={form.bay_id} onChange={(e) => setForm({ ...form, bay_id: Number(e.target.value) })}>
          {bays.data?.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
        </SelectField>
        <Field label="Fecha programada" type="date" value={form.scheduled_date} onChange={(e) => setForm({ ...form, scheduled_date: e.target.value })} />
        <Field label="Fecha compromiso" type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
        <div className="sm:col-span-2"><Field label="Notas" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></div>
      </div>
      {error && <div className="mt-3"><Notice kind="danger">{error}</Notice></div>}
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="ghost" onClick={onClose}>Cancelar</Button>
        <Button variant="primary" icon={ClipboardPlus} loading={busy} disabled={!form.customer || !items.length} onClick={submit}>Crear orden</Button>
      </div>
    </Modal>
  );
}
