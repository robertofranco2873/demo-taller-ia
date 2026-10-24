import { AnimatePresence, motion } from "framer-motion";
import { Bot, ClipboardPlus, FileSpreadsheet, FileText, MessageCircle, Minus, Plus, Receipt, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Field, SelectField, TextArea } from "../components/fields";
import { NewOrderModal } from "../components/NewOrderModal";
import { Skeleton } from "../components/Skeleton";
import { Button, Card, InfoTip, Modal, Notice, PageHeader, Tooltip, useToast } from "../components/ui";
import { api } from "../lib/api";
import { hours, money, pct } from "../lib/format";
import { useApi, useCountUp, useDebounced } from "../lib/hooks";
import type { Quote, Service, Settings } from "../lib/types";

interface Suggestion { codigo: string; nombre: string; service_id: number; motivo: string; confianza: number }
interface Diagnosis { servicios: Suggestion[]; preguntas: string[]; nota: string; descartados: string[] }

function Total({ value }: { value: number }) {
  const v = useCountUp(value, 0.5);
  return <>{money(v ?? 0)}</>;
}

export default function Cotizador() {
  const toast = useToast();
  const services = useApi<Service[]>("/api/services");
  const settings = useApi<Settings>("/api/settings");
  const ai = useApi<{ enabled: boolean; model: string | null }>("/api/ai/status");
  const [items, setItems] = useState<{ service_id: number; qty: number }[]>([{ service_id: 3, qty: 1 }, { service_id: 8, qty: 1 }]);
  const [rate, setRate] = useState<number | null>(null);
  const [margin, setMargin] = useState<number | null>(null);
  const [client, setClient] = useState({ customer: "Cliente de prueba (ficticio)", phone: "+52 55 0000 0000", vehicle: "Nissan Versa 2018" });
  const [quote, setQuote] = useState<Quote | null>(null);
  const [quoting, setQuoting] = useState(false);
  const [problem, setProblem] = useState("");
  const [diag, setDiag] = useState<Diagnosis | null>(null);
  const [diagBusy, setDiagBusy] = useState(false);
  const [whatsapp, setWhatsapp] = useState<string | null>(null);
  const [waBusy, setWaBusy] = useState(false);
  const [orderOpen, setOrderOpen] = useState(false);

  useEffect(() => {
    if (settings.data && rate === null) {
      setRate(settings.data.labor_rate);
      setMargin(settings.data.margin_pct);
    }
  }, [settings.data, rate]);

  const body = useMemo(() => ({ items, labor_rate: rate, margin_pct: margin, ...client }), [items, rate, margin, client]);
  const debounced = useDebounced(body, 250);

  useEffect(() => {
    if (!debounced.items.length || debounced.labor_rate === null) {
      setQuote(null);
      return;
    }
    let alive = true;
    setQuoting(true);
    api.post<Quote>("/api/quotes", debounced).then((q) => alive && setQuote(q)).catch((e) => alive && toast((e as Error).message, "danger")).finally(() => alive && setQuoting(false));
    return () => {
      alive = false;
    };
  }, [debounced, toast]);

  const byId = useMemo(() => new Map((services.data ?? []).map((s) => [s.id, s])), [services.data]);
  const add = (sid: number) => sid && setItems((it) => (it.some((i) => i.service_id === sid) ? it : [...it, { service_id: sid, qty: 1 }]));
  const setQty = (sid: number, d: number) => setItems((it) => it.map((i) => (i.service_id === sid ? { ...i, qty: Math.max(1, Math.min(20, i.qty + d)) } : i)));

  async function diagnose() {
    setDiagBusy(true);
    try {
      const r = await api.post<Diagnosis>("/api/ai/diagnosis", { problem });
      setDiag(r);
      if (r.servicios.length) {
        setItems(r.servicios.map((s) => ({ service_id: s.service_id, qty: 1 })));
        toast(`La IA sugirió ${r.servicios.length} servicio(s). El precio lo calcula la fórmula.`, "info");
      }
    } catch (e) {
      toast((e as Error).message, "danger");
    } finally {
      setDiagBusy(false);
    }
  }

  async function writeWhatsapp() {
    setWaBusy(true);
    try {
      setWhatsapp((await api.post<{ text: string }>("/api/ai/whatsapp", body)).text);
    } catch (e) {
      toast((e as Error).message, "danger");
    } finally {
      setWaBusy(false);
    }
  }

  const file = (ext: string) => `cotizacion_${new Date().toISOString().slice(0, 10)}.${ext}`;

  return (
    <div>
      <PageHeader icon={Receipt} title="Cotizador por fórmula" subtitle="Horas estándar × tarifa + refacciones, más margen e IVA"
        crumbs={[{ label: "Operación" }, { label: "Cotizador" }]} />
      <div className="grid gap-4 lg:grid-cols-5">
        <div className="space-y-4 lg:col-span-3">
          <Card title={<span className="inline-flex items-center gap-2"><Bot size={18} className="text-accent" aria-hidden />Diagnóstico a cotización (IA)</span>}
            actions={ai.data?.enabled && <span className="text-xs text-muted">Modelo: {ai.data.model}</span>}>
            {ai.loading ? <Skeleton className="h-20" /> : ai.data?.enabled ? (
              <>
                <TextArea label="¿Qué le pasa al vehículo? (texto libre)" value={problem} onChange={(e) => setProblem(e.target.value)} placeholder="El carro hace ruido al frenar y vibra el volante" />
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <Button variant="primary" icon={Sparkles} loading={diagBusy} disabled={problem.trim().length < 5} onClick={diagnose}>Sugerir servicios</Button>
                  <span className="text-xs text-muted">La IA solo sugiere servicios del catálogo (JSON validado); nunca calcula precios.</span>
                </div>
                <AnimatePresence>
                  {diag && (
                    <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="mt-3 space-y-2 overflow-hidden">
                      {diag.servicios.map((s) => (
                        <div key={s.codigo} className="flex items-start justify-between gap-3 rounded-md bg-accent-soft p-3">
                          <div><div className="text-sm font-semibold text-text">{s.codigo} · {s.nombre}</div><div className="text-xs text-secondary">{s.motivo}</div></div>
                          <Tooltip content="Qué tan segura está la IA de esta sugerencia."><span className="shrink-0 rounded-full bg-surface-solid px-2 py-0.5 text-xs font-medium text-accent">{pct(s.confianza)}</span></Tooltip>
                        </div>
                      ))}
                      {diag.preguntas.length > 0 && <Notice kind="info"><b>Pregunta al cliente:</b> {diag.preguntas.join(" · ")}</Notice>}
                      {diag.descartados.length > 0 && <p className="text-xs text-muted">Descartados por no estar en el catálogo: {diag.descartados.join(", ")}</p>}
                    </motion.div>
                  )}
                </AnimatePresence>
              </>
            ) : (
              <Notice kind="info">Funciones de IA desactivadas (no hay <code>GROQ_API_KEY</code>). El cotizador funciona completo sin ellas.</Notice>
            )}
          </Card>

          <Card title="Servicios a cotizar">
            <SelectField label="Agregar servicio del catálogo" value="" onChange={(e) => add(Number(e.target.value))}>
              <option value="">Elige un servicio…</option>
              {services.data?.map((s) => <option key={s.id} value={s.id}>{s.code} · {s.name} ({hours(s.std_hours)})</option>)}
            </SelectField>
            <ul className="mt-3 space-y-2">
              <AnimatePresence initial={false}>
                {items.map((i) => {
                  const s = byId.get(i.service_id);
                  return (
                    <motion.li key={i.service_id} layout initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 10 }}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-surface-muted px-3 py-2">
                      <span className="text-sm text-text">{s ? `${s.code} · ${s.name}` : "…"}<span className="ml-2 text-xs text-muted">{s && hours(s.std_hours)}</span></span>
                      <span className="flex items-center gap-1">
                        <button type="button" onClick={() => setQty(i.service_id, -1)} className="cursor-pointer rounded-md p-1.5 hover:bg-surface-solid" aria-label="Menos"><Minus size={14} /></button>
                        <span className="w-6 text-center text-sm font-semibold tabular-nums">{i.qty}</span>
                        <button type="button" onClick={() => setQty(i.service_id, 1)} className="cursor-pointer rounded-md p-1.5 hover:bg-surface-solid" aria-label="Más"><Plus size={14} /></button>
                        <button type="button" onClick={() => setItems(items.filter((x) => x.service_id !== i.service_id))} className="cursor-pointer rounded-md p-1.5 text-danger hover:bg-danger-soft" aria-label="Quitar"><Trash2 size={14} /></button>
                      </span>
                    </motion.li>
                  );
                })}
              </AnimatePresence>
            </ul>
            {!items.length && <p className="py-4 text-center text-sm text-muted">Agrega servicios o usa el diagnóstico con IA.</p>}
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <Field label="Tarifa por hora estándar (MXN)" type="number" min={0} step={10} value={rate ?? ""} onChange={(e) => setRate(Number(e.target.value))} />
              <Field label="Margen (%)" type="number" min={0} step={1} value={margin === null ? "" : Math.round(margin * 100)} onChange={(e) => setMargin(Number(e.target.value) / 100)} />
              <Field label="Cliente" value={client.customer} onChange={(e) => setClient({ ...client, customer: e.target.value })} />
              <Field label="Vehículo" value={client.vehicle} onChange={(e) => setClient({ ...client, vehicle: e.target.value })} />
            </div>
          </Card>
        </div>

        <div className="lg:col-span-2">
          <Card className="lg:sticky lg:top-24" title="Cotización">
            {!quote ? <div className="space-y-2">{[1, 2, 3, 4].map((k) => <Skeleton key={k} className="h-6" />)}</div> : (
              <div className={quoting ? "opacity-70 transition-opacity" : ""}>
                <ul className="space-y-1.5 text-sm">
                  {quote.lines.map((l) => (
                    <li key={l.code} className="flex justify-between gap-2"><span className="text-secondary">{l.qty} × {l.name}</span><span className="tabular-nums">{money(l.subtotal)}</span></li>
                  ))}
                </ul>
                <hr className="my-3 border-border" />
                {[
                  ["Horas estándar", hours(quote.horas_estandar), "Σ tiempo estándar × cantidad"],
                  ["Mano de obra", money(quote.mano_de_obra), `horas × ${money(quote.labor_rate)}`],
                  ["Refacciones", money(quote.refacciones), "Σ precio de refacciones del catálogo"],
                  [`Margen ${pct(quote.margin_pct)}`, money(quote.margen), "(mano de obra + refacciones) × margen"],
                  ["Subtotal", money(quote.subtotal), "base + margen"],
                  [`IVA ${pct(quote.iva_rate)}`, money(quote.iva), "subtotal × 16 %"],
                ].map(([label, value, f]) => (
                  <div key={label} className="flex items-center justify-between py-0.5 text-sm">
                    <span className="inline-flex items-center gap-1 text-secondary">{label}<InfoTip text="Cómo se calcula" formula={f} /></span>
                    <span className="tabular-nums text-text">{value}</span>
                  </div>
                ))}
                <div className="mt-3 flex items-center justify-between rounded-md p-3 text-on-accent [background:var(--gradient-brand)]">
                  <span className="font-medium">TOTAL</span>
                  <span className="text-2xl font-bold tabular-nums"><Total value={quote.total} /></span>
                </div>
                <p className="mt-2 text-xs text-muted">{quote.formula}</p>
                <div className="mt-4 grid grid-cols-2 gap-2">
                  <Button icon={FileSpreadsheet} onClick={() => api.download("/api/quotes/excel", file("xlsx"), body).catch((e) => toast(e.message, "danger"))}>Excel</Button>
                  <Button icon={FileText} onClick={() => api.download("/api/quotes/pdf", file("pdf"), body).catch((e) => toast(e.message, "danger"))}>PDF</Button>
                  {ai.data?.enabled && <Button icon={MessageCircle} loading={waBusy} onClick={writeWhatsapp} className="col-span-2">Mensaje de WhatsApp (IA)</Button>}
                  <Button variant="primary" icon={ClipboardPlus} onClick={() => setOrderOpen(true)} className="col-span-2">Convertir en orden</Button>
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>

      <Modal open={whatsapp !== null} onClose={() => setWhatsapp(null)} title="Mensaje de WhatsApp" subtitle="Revísalo antes de enviarlo: los importes vienen de la fórmula">
        <textarea className="field min-h-56" value={whatsapp ?? ""} onChange={(e) => setWhatsapp(e.target.value)} aria-label="Mensaje" />
        <div className="mt-3 flex justify-end">
          <Button variant="primary" onClick={() => { navigator.clipboard?.writeText(whatsapp ?? ""); toast("Mensaje copiado."); }}>Copiar</Button>
        </div>
      </Modal>
      <NewOrderModal open={orderOpen} onClose={() => setOrderOpen(false)} draft={{ ...client, items }} />
    </div>
  );
}
