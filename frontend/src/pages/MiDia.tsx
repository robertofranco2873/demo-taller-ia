import { AnimatePresence, motion } from "framer-motion";
import { BookOpen, CarFront, CheckCheck, Clock3, Flag, MapPin, Pause, Play, Timer, Wrench } from "lucide-react";
import { useEffect, useState } from "react";
import { ThemedLoader } from "../components/loaders";
import { Button, Card, ErrorState, InfoTip, Modal, Notice, PageHeader, StatusBadge, useToast } from "../components/ui";
import { api } from "../lib/api";
import { celebrateGoal, celebrateOrder } from "../lib/celebrate";
import { date, duration, hours, money, pct } from "../lib/format";
import { useApi } from "../lib/hooks";
import type { Timer as TimerT } from "../lib/types";

interface DayService { id: number; code: string; name: string; qty: number; std_hours: number; steps: string[] }
interface DayOrder {
  id: number; folio: string; status: string; customer: string; vehicle: string; bay: string; due_date: string;
  scheduled_date: string; std_hours: number; notes: string; priority: "vencida" | "hoy" | "próxima"; timer: TimerT;
  services: DayService[];
}
interface Day { date: string; technician: string; orders: DayOrder[]; finished_today: number; today_hours: number }
interface ServiceDetail { name: string; code: string; std_hours: number; steps: string[]; parts: { code: string; name: string; qty: number; importe: number }[]; stats: { real_promedio_h: number | null } }

/**
 * Horas en vivo: timer.hours (calculado por el servidor al responder) + lo transcurrido desde entonces.
 * Así no depende de la zona horaria del servidor.
 */
function useLiveHours(timer: TimerT, fetchedAt: number) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!timer.running) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [timer.running]);
  return timer.running ? timer.hours + Math.max(0, (now - fetchedAt) / 3_600_000) : timer.hours;
}

function OrderCard({ order, fetchedAt, onChange, onSheet }: { order: DayOrder; fetchedAt: number; onChange: () => void; onSheet: (id: number) => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState<string | null>(null);
  const [confirmFinish, setConfirmFinish] = useState(false);
  const live = useLiveHours(order.timer, fetchedAt);
  // Terminar con muy poco tiempo registrado suele ser un error (daría eficiencias absurdas).
  const suspicious = live < order.std_hours * 0.25;
  const progress = Math.min(1.5, live / Math.max(order.std_hours, 0.01));

  async function act(action: "start" | "pause" | "finish") {
    setBusy(action);
    try {
      const res = await api.post<{ efficiency?: number; goal_reached?: boolean; goal?: number; counts_for_kpis?: boolean }>(`/api/me/orders/${order.id}/${action}`);
      if (action === "finish") {
        celebrateOrder();
        toast(res.counts_for_kpis === false
          ? `${order.folio} terminada. El tiempo registrado es menor al 25 % del estándar: no cuenta para tus indicadores.`
          : `¡${order.folio} terminada! Eficiencia ${pct(res.efficiency ?? null)}.`, res.counts_for_kpis === false ? "info" : "success");
        if (res.goal_reached) {
          setTimeout(celebrateGoal, 500);
          toast(`🏆 Superaste la meta de eficiencia (${pct(res.goal ?? null)}).`, "info");
        }
      }
      onChange();
    } catch (e) {
      toast((e as Error).message, "danger");
    } finally {
      setBusy(null);
    }
  }

  const ring = order.priority === "vencida" ? "border-l-[var(--danger)]" : order.priority === "hoy" ? "border-l-[var(--gold-vivid)]" : "border-l-[var(--blue-500)]";
  return (
    <motion.div layout initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }}>
      <Card className={`border-l-4 ${ring}`}>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-lg font-bold text-text">{order.folio}</span>
              <StatusBadge status={order.priority} />
              <StatusBadge status={order.status} />
            </div>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-secondary">
              <span className="inline-flex items-center gap-1"><CarFront size={14} aria-hidden />{order.vehicle}</span>
              <span className="inline-flex items-center gap-1"><MapPin size={14} aria-hidden />{order.bay}</span>
              <span className="inline-flex items-center gap-1"><Flag size={14} aria-hidden />Compromiso {date(order.due_date)}</span>
            </div>
          </div>
          <div className="text-right">
            <div className="flex items-center justify-end gap-1 text-xs text-muted">
              Tiempo real <InfoTip text="Lo mide el cronómetro. Al terminar se reparte entre los servicios según su tiempo estándar." />
            </div>
            <div className={`font-mono text-3xl font-bold tabular-nums ${order.timer.running ? "text-accent" : "text-text"}`} aria-live="off">
              {duration(live)}
            </div>
            <div className="text-xs text-muted">Estándar {hours(order.std_hours)}</div>
          </div>
        </div>

        <div className="mt-3 h-2 overflow-hidden rounded-full bg-surface-muted" role="progressbar" aria-label="Avance vs. tiempo estándar" aria-valuenow={Math.round(progress * 100)} aria-valuemin={0} aria-valuemax={150}>
          <motion.div className="h-full rounded-full" style={{ background: progress > 1 ? "var(--danger)" : "var(--gradient-brand)" }} animate={{ width: `${Math.min(progress, 1) * 100}%` }} />
        </div>

        <ul className="mt-3 space-y-1.5">
          {order.services.map((s) => (
            <li key={s.id} className="flex items-center justify-between gap-2 rounded-md bg-surface-muted px-3 py-2">
              <span className="text-sm text-text"><Wrench size={14} className="mr-1.5 inline text-accent" aria-hidden />{s.code} · {s.name}{s.qty > 1 && ` ×${s.qty}`}</span>
              <button type="button" onClick={() => onSheet(s.id)} className="inline-flex shrink-0 cursor-pointer items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-link hover:bg-accent-soft">
                <BookOpen size={13} aria-hidden /> Ficha
              </button>
            </li>
          ))}
        </ul>
        {order.notes && <p className="mt-2 text-xs text-muted">Notas: {order.notes}</p>}

        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {order.timer.running ? (
            <Button size="xl" variant="secondary" icon={Pause} loading={busy === "pause"} onClick={() => act("pause")}>Pausar</Button>
          ) : (
            <Button size="xl" variant="primary" icon={Play} loading={busy === "start"} onClick={() => act("start")}>
              {order.timer.hours > 0 ? "Reanudar" : "Iniciar"}
            </Button>
          )}
          <Button size="xl" variant="gold" icon={CheckCheck} loading={busy === "finish"} disabled={order.timer.hours <= 0 && !order.timer.running}
            onClick={() => (suspicious ? setConfirmFinish(true) : act("finish"))} className="sm:col-span-2">
            Terminar
          </Button>
        </div>
      </Card>
      <Modal open={confirmFinish} onClose={() => setConfirmFinish(false)} title={`¿Terminar ${order.folio}?`}>
        <Notice kind="warning">
          El cronómetro registra {duration(live)}, mucho menos que el estándar ({hours(order.std_hours)}). Si olvidaste iniciarlo, la eficiencia quedará distorsionada.
        </Notice>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setConfirmFinish(false)}>Seguir trabajando</Button>
          <Button variant="gold" icon={CheckCheck} onClick={() => { setConfirmFinish(false); act("finish"); }}>Terminar de todos modos</Button>
        </div>
      </Modal>
    </motion.div>
  );
}

function ServiceSheet({ id, onClose }: { id: number | null; onClose: () => void }) {
  const { data, loading } = useApi<ServiceDetail>(id ? `/api/services/${id}` : null);
  return (
    <Modal open={id !== null} onClose={onClose} title={data ? `${data.code} · ${data.name}` : "Ficha del servicio"} subtitle="Ficha rápida">
      {loading || !data ? <ThemedLoader kind="wrench" label="Abriendo ficha…" /> : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-md bg-accent-soft p-3"><div className="text-xs text-secondary">Tiempo estándar</div><div className="text-xl font-bold text-text">{hours(data.std_hours)}</div></div>
            <div className="rounded-md bg-surface-muted p-3"><div className="text-xs text-secondary">Real promedio del taller</div><div className="text-xl font-bold text-text">{hours(data.stats.real_promedio_h)}</div></div>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold text-text">Pasos</h3>
            <ol className="space-y-2">
              {data.steps.map((s, i) => (
                <li key={i} className="flex gap-3 text-sm text-text">
                  <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-bold text-on-accent [background:var(--gradient-brand)]">{i + 1}</span>
                  {s}
                </li>
              ))}
            </ol>
          </div>
          <div>
            <h3 className="mb-2 text-sm font-semibold text-text">Refacciones</h3>
            {data.parts.length ? (
              <ul className="space-y-1 text-sm">
                {data.parts.map((p) => <li key={p.code} className="flex justify-between gap-2"><span>{p.qty} × {p.name}</span><span className="text-muted">{money(p.importe)}</span></li>)}
              </ul>
            ) : <p className="text-sm text-muted">Solo mano de obra.</p>}
          </div>
        </div>
      )}
    </Modal>
  );
}

export default function MiDia() {
  const { data, error, loading, reload } = useApi<Day>("/api/me/day");
  const [sheet, setSheet] = useState<number | null>(null);
  const [stamp, setStamp] = useState(() => Date.now());
  useEffect(() => {
    if (data) setStamp(Date.now());
  }, [data]);

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (loading && !data) return <ThemedLoader kind="wrench" label="Preparando tu día…" />;
  if (!data) return null;
  const orders = data.orders;
  const today = new Date().toLocaleDateString("es-MX", { weekday: "long", day: "numeric", month: "long" });

  return (
    <div>
      <PageHeader icon={Timer} title="Mi día" subtitle={<span className="capitalize">{today} · {data.technician}</span>} />
      <div className="mb-5 grid grid-cols-3 gap-3">
        {[
          { label: "Pendientes", value: String(data.orders.length), icon: Clock3 },
          { label: "Horas para hoy", value: hours(data.today_hours), icon: Timer },
          { label: "Terminadas hoy", value: String(data.finished_today), icon: CheckCheck },
        ].map((s) => (
          <Card key={s.label} hover padded={false} className="p-3 text-center sm:p-4">
            <s.icon size={18} className="mx-auto mb-1 text-accent" aria-hidden />
            <div className="text-xl font-bold text-text">{s.value}</div>
            <div className="text-xs text-muted">{s.label}</div>
          </Card>
        ))}
      </div>
      <Notice kind="info">Ordenadas por prioridad: primero las vencidas, luego las que vencen hoy. Usa <strong>Iniciar</strong>, <strong>Pausar</strong> y <strong>Terminar</strong>: el cronómetro registra tu tiempo real.</Notice>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <AnimatePresence>
          {orders.map((o) => <OrderCard key={o.id} order={o} fetchedAt={stamp} onChange={reload} onSheet={setSheet} />)}
        </AnimatePresence>
      </div>
      {!orders.length && <Card className="mt-4 text-center text-secondary">No tienes órdenes pendientes. ¡Buen trabajo! 🎉</Card>}
      <ServiceSheet id={sheet} onClose={() => setSheet(null)} />
    </div>
  );
}
