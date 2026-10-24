import { ArrowDown, ArrowUp, Hand, ListOrdered, RotateCcw, Shuffle, Trophy } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { Chart } from "../components/Chart";
import { SelectField } from "../components/fields";
import { Table } from "../components/Table";
import { Button, Card, ErrorState, InfoTip, Modal, Notice, PageHeader, Segmented, StatusBadge, useToast } from "../components/ui";
import { api } from "../lib/api";
import { useChartColors } from "../lib/chartTheme";
import { ganttDaysOption, type GanttDay } from "../lib/charts";
import { date, dateTime, num } from "../lib/format";
import { useApi, useDebounced } from "../lib/hooks";
import type { Technician } from "../lib/types";

type Rule = "FIFO" | "SPT" | "EDD" | "MANUAL";
type Mode = "assigned" | "shop" | "technician";
interface Comparison { regla: Rule; flujo_promedio_h: number; retraso_promedio_h: number; ordenes_tarde: number; makespan_h: number }
interface SchedRow {
  posicion: number; orden: string; recurso: string; bahia: string; proceso_h: number; entrega_h: number;
  inicio_h: number; fin_h: number; inicio: string; fin: string; retraso_h: number; tarde: boolean;
  compromiso: string; cliente: string; vehiculo: string; estado: string; prioridad_guardada: number | null;
}
interface Seq {
  jobs: number; hours: number; now: string; rules: Record<Rule, string>; comparison: Comparison[];
  schedule: SchedRow[]; days: GanttDay[]; technicians: string[]; has_manual: boolean;
}

const RULE_OPTIONS: { value: Rule; label: string }[] = [
  { value: "FIFO", label: "FIFO" }, { value: "SPT", label: "SPT" }, { value: "EDD", label: "EDD" }, { value: "MANUAL", label: "Manual" },
];
const short = (n: string) => n.split("·")[1]?.trim() ?? n;

/** Carga la propuesta: GET para reglas y prioridades guardadas; POST /simulate cuando el usuario reordena. */
function useSequencing(rule: Rule, mode: Mode, tech: number, order: string[] | null) {
  const [data, setData] = useState<Seq | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const req = useDebounced(JSON.stringify({ rule, mode, tech, order }), 250);

  useEffect(() => {
    const { rule: r, mode: m, tech: t, order: o } = JSON.parse(req) as { rule: Rule; mode: Mode; tech: number; order: string[] | null };
    const technician_id = m === "technician" ? t : null;
    let alive = true;
    setLoading(true);
    setError(null);
    const call = r === "MANUAL" && o
      ? api.post<Seq>("/api/sequencing/simulate", { rule: r, mode: m, technician_id, priorities: Object.fromEntries(o.map((f, i) => [f, i + 1])) })
      : api.get<Seq>("/api/sequencing", { rule: r, mode: m, technician_id });
    call.then((d) => alive && setData(d)).catch((e: Error) => alive && setError(e.message)).finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [req, tick]);
  return { data, error, loading, reload: () => setTick((x) => x + 1) };
}

function PriorityCell({ row, total, visibleIndex, visibleCount, onUp, onDown, onSet }: {
  row: SchedRow; total: number; visibleIndex: number; visibleCount: number;
  onUp: () => void; onDown: () => void; onSet: (n: number) => void;
}) {
  const [value, setValue] = useState(String(row.posicion));
  useEffect(() => setValue(String(row.posicion)), [row.posicion]);
  const commit = () => {
    const n = Math.round(Number(value));
    if (Number.isFinite(n) && n >= 1 && n <= total && n !== row.posicion) onSet(n);
    else setValue(String(row.posicion));
  };
  return (
    <span className="inline-flex items-center gap-1" onClick={(e) => e.stopPropagation()} onKeyDown={(e) => e.stopPropagation()}>
      <button type="button" onClick={onUp} disabled={visibleIndex === 0} aria-label={`Subir prioridad de ${row.orden}`}
        className="cursor-pointer rounded-md p-1 text-secondary hover:bg-accent-soft hover:text-accent disabled:cursor-not-allowed disabled:opacity-30"><ArrowUp size={15} /></button>
      <button type="button" onClick={onDown} disabled={visibleIndex === visibleCount - 1} aria-label={`Bajar prioridad de ${row.orden}`}
        className="cursor-pointer rounded-md p-1 text-secondary hover:bg-accent-soft hover:text-accent disabled:cursor-not-allowed disabled:opacity-30"><ArrowDown size={15} /></button>
      <input type="number" min={1} max={total} value={value} aria-label={`Prioridad de ${row.orden}`}
        onChange={(e) => setValue(e.target.value)} onBlur={commit} onKeyDown={(e) => e.key === "Enter" && (e.currentTarget as HTMLInputElement).blur()}
        className="field h-8 w-14 px-2 text-center font-semibold tabular-nums" />
    </span>
  );
}

export default function Secuenciacion() {
  const c = useChartColors();
  const toast = useToast();
  const [rule, setRule] = useState<Rule>("EDD");
  const [mode, setMode] = useState<Mode>("assigned");
  const [tech, setTech] = useState(1);
  const [order, setOrder] = useState<string[] | null>(null);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const techs = useApi<Technician[]>("/api/technicians");
  const { data, error, loading, reload } = useSequencing(rule, mode, tech, order);

  // Si ya hay una secuencia guardada (de un "Reasignar" anterior), se abre en modo Manual.
  const openedStored = useRef(false);
  useEffect(() => {
    if (data && !openedStored.current) {
      openedStored.current = true;
      if (data.has_manual) setRule("MANUAL");
    }
  }, [data]);

  const sorted = useMemo(() => [...(data?.schedule ?? [])].sort((a, b) => a.posicion - b.posicion), [data]);
  const visible = filter ? sorted.filter((r) => r.recurso === filter) : sorted;
  const resources = filter ? [filter] : data?.technicians ?? [];

  const baseOrder = () => order ?? sorted.map((r) => r.orden);
  function applyOrder(next: string[]) {
    setOrder(next);
    setRule("MANUAL");
  }
  function moveRelative(folio: string, target: string, after: boolean) {
    const arr = baseOrder().filter((f) => f !== folio);
    const idx = arr.indexOf(target);
    arr.splice(after ? idx + 1 : idx, 0, folio);
    applyOrder(arr);
  }
  function moveToPosition(folio: string, n: number) {
    const arr = baseOrder().filter((f) => f !== folio);
    arr.splice(n - 1, 0, folio);
    applyOrder(arr);
  }
  function changeRule(r: Rule) {
    setOrder(null); // una regla automática (o la secuencia guardada) reemplaza el orden editado
    setRule(r);
  }
  function changeMode(m: Mode) {
    setOrder(null);
    setFilter("");
    setMode(m);
  }

  async function apply() {
    setBusy(true);
    try {
      const priorities = rule === "MANUAL" ? Object.fromEntries((order ?? sorted.map((r) => r.orden)).map((f, i) => [f, i + 1])) : null;
      const r = await api.post<{ updated: number }>("/api/sequencing/apply", {
        rule, mode: mode === "assigned" && rule !== "MANUAL" ? "shop" : mode, technician_id: mode === "technician" ? tech : null, priorities,
      });
      toast(`Secuencia guardada en ${r.updated} órdenes (prioridad, técnico, bahía y fecha). Los técnicos la verán en Mi día.`);
      setConfirm(false);
      setOrder(null);
      setRule("MANUAL");
      reload();
    } catch (e) {
      toast((e as Error).message, "danger");
    } finally {
      setBusy(false);
    }
  }

  if (error && !data) return <ErrorState message={error} onRetry={reload} />;
  const best = (k: keyof Comparison) => (data?.comparison.length ? data.comparison.reduce((a, b) => (Number(b[k]) < Number(a[k]) ? b : a)).regla : null);
  const edited = rule === "MANUAL" && order !== null;
  const lateCount = visible.filter((r) => r.tarde).length;

  return (
    <div>
      <PageHeader icon={ListOrdered} title="Secuenciación de órdenes pendientes" subtitle="Reglas FIFO, SPT, EDD o prioridad manual, con técnicos y bahías como recursos"
        crumbs={[{ label: "Análisis" }, { label: "Secuenciación" }]}
        actions={<Button variant="gold" icon={Shuffle} onClick={() => setConfirm(true)} disabled={!data?.jobs}>Guardar / reasignar</Button>} />

      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <Segmented label="Alcance" value={mode} onChange={changeMode} options={[
            { value: "assigned", label: "Respetar asignación" }, { value: "shop", label: "Taller completo" }, { value: "technician", label: "Por técnico" },
          ]} />
          {mode === "technician" && (
            <div className="w-64"><SelectField label="Técnico" value={tech} onChange={(e) => { setOrder(null); setTech(Number(e.target.value)); }}>{techs.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</SelectField></div>
          )}
          <InfoTip text="Cada orden usa un técnico y una bahía; inicia cuando ambos están libres. «Taller completo» asigna al técnico que se libera primero." formula="Flujo = fin · Retraso = máx(0, fin − compromiso)" />
        </div>
        {data && <p className="mt-3 text-xs text-muted">{data.jobs} órdenes · {num(data.hours)} h estándar · inicio {dateTime(data.now)} · horas laborables (lunes a sábado, 9:00 a 17:00)</p>}
      </Card>

      <Card className="mt-4" title="Comparativa de reglas">
        <Table rows={data?.comparison} loading={!data} rowKey={(r) => r.regla} onRowClick={(r) => changeRule(r.regla)} columns={[
          { key: "r", header: "Regla", render: (r) => <span className="inline-flex items-center gap-2 font-semibold">{r.regla === rule && <span className="h-2 w-2 rounded-full [background:var(--gold-vivid)]" aria-label="seleccionada" />}{r.regla === "MANUAL" ? "Manual" : r.regla}<span className="hidden text-xs font-normal text-muted md:inline">{data?.rules[r.regla]}</span></span> },
          { key: "f", header: "Flujo prom.", numeric: true, render: (r) => <span className={best("flujo_promedio_h") === r.regla ? "font-bold text-success" : ""}>{best("flujo_promedio_h") === r.regla && <Trophy size={12} className="mr-1 inline" aria-label="mejor" />}{num(r.flujo_promedio_h)} h</span> },
          { key: "t", header: "Retraso prom.", numeric: true, render: (r) => <span className={best("retraso_promedio_h") === r.regla ? "font-bold text-success" : ""}>{best("retraso_promedio_h") === r.regla && <Trophy size={12} className="mr-1 inline" aria-label="mejor" />}{num(r.retraso_promedio_h)} h</span> },
          { key: "l", header: "Tarde", numeric: true, render: (r) => <span className={best("ordenes_tarde") === r.regla ? "font-bold text-success" : ""}>{r.ordenes_tarde}</span> },
          { key: "m", header: "Makespan", numeric: true, render: (r) => `${num(r.makespan_h)} h` },
        ]} />
      </Card>

      <Card className="mt-4"
        title={<span className="inline-flex items-center gap-2">Secuencia propuesta{edited && <span className="inline-flex items-center gap-1 rounded-full bg-gold-soft px-2 py-0.5 text-xs font-medium text-gold"><Hand size={12} aria-hidden />editada, sin guardar</span>}</span>}
        actions={<>
          <Segmented label="Regla" value={rule} onChange={changeRule} options={RULE_OPTIONS} />
          {mode !== "technician" && (
            <div className="w-52"><SelectField label="Ver técnico" value={filter} onChange={(e) => { setFilter(e.target.value); setSelected(null); }}>
              <option value="">Todos</option>
              {data?.technicians.map((t) => <option key={t} value={t}>{t}</option>)}
            </SelectField></div>
          )}
          {edited && <Button size="sm" variant="ghost" icon={RotateCcw} onClick={() => changeRule("EDD")}>Restablecer</Button>}
        </>}>
        <p className="mb-3 text-xs text-muted">
          Cambia la prioridad con las flechas o escribe el número (1 = primero): el programa y el Gantt se recalculan con la regla <b>Manual</b>.
          Clic en una fila para resaltarla en el Gantt. <b>Guardar / reasignar</b> fija la secuencia y los técnicos la verán en Mi día.
        </p>
        {data && visible.length > 0 && (
          <div className="mb-3"><Notice kind={lateCount ? "warning" : "success"}>{filter ? short(filter) : "Taller"}: {visible.length} órdenes · {lateCount} saldrían tarde con esta secuencia.</Notice></div>
        )}
        <div className={loading ? "opacity-60 transition-opacity" : "transition-opacity"}>
          <Table rows={data ? visible : null} rowKey={(s) => s.orden} maxHeight={440} onRowClick={(s) => setSelected((x) => (x === s.orden ? null : s.orden))} columns={[
            { key: "p", header: <span className="inline-flex items-center gap-1">Prioridad<InfoTip text="Orden de atención. En «Respetar asignación» cada técnico atiende sus órdenes en este orden; la prioridad también decide quién toma primero una bahía libre." /></span>,
              render: (s) => {
                const i = visible.indexOf(s);
                return <PriorityCell row={s} total={sorted.length} visibleIndex={i} visibleCount={visible.length}
                  onUp={() => moveRelative(s.orden, visible[i - 1].orden, false)}
                  onDown={() => moveRelative(s.orden, visible[i + 1].orden, true)}
                  onSet={(n) => moveToPosition(s.orden, n)} />;
              } },
            { key: "o", header: "Orden", render: (s) => <span className={selected === s.orden ? "font-bold text-accent" : "font-semibold text-text"}>{s.orden}<span className="block text-xs font-normal text-muted">{s.cliente}</span></span> },
            { key: "r", header: "Técnico", render: (s) => short(s.recurso) },
            { key: "b", header: "Bahía", hideOnMobile: true, render: (s) => s.bahia },
            { key: "h", header: "Proceso", numeric: true, render: (s) => `${num(s.proceso_h, 2)} h` },
            { key: "c", header: "Compromiso", hideOnMobile: true, render: (s) => date(s.compromiso) },
            { key: "i", header: "Inicio", render: (s) => dateTime(s.inicio) },
            { key: "f", header: "Fin", hideOnMobile: true, render: (s) => dateTime(s.fin) },
            { key: "x", header: "Retraso", numeric: true, render: (s) => (s.tarde
              ? <span className="inline-flex items-center gap-1.5 font-medium text-danger">{num(s.retraso_h)} h <StatusBadge status="vencida" /></span>
              : <span className="text-success">a tiempo</span>) },
          ]} />
        </div>
      </Card>

      <Card className="mt-4" title={`Diagrama de Gantt por día · ${rule === "MANUAL" ? "Manual" : rule}${filter ? ` · ${short(filter)}` : ""}`}>
        <Chart loading={!data} height={Math.max(260, resources.length * 78 + 110)} ariaLabel={`Diagrama de Gantt por día, regla ${rule}`}
          option={ganttDaysOption(c, visible.map((s) => ({
            resource: s.recurso, folio: s.orden, start: s.inicio_h, end: s.fin_h, late: s.tarde, bay: s.bahia,
            priority: s.posicion, inicio: s.inicio, fin: s.fin, customer: s.cliente,
          })), resources, data?.days ?? [], selected)} />
        <p className="mt-1 text-xs text-muted">Cada franja es un día laborable (9:00 a 17:00). Azul = a tiempo · Rojo = tarde · #n = prioridad. Arrastra la barra inferior o usa la rueda para ver más días.</p>
      </Card>

      <Modal open={confirm} onClose={() => setConfirm(false)} title="¿Guardar esta secuencia?" subtitle={rule === "MANUAL" ? "Prioridad manual" : `Regla ${rule}`}>
        <Notice kind="warning">
          Se guardará la prioridad de las {data?.jobs} órdenes pendientes y se actualizará su técnico, bahía y fecha programada según la propuesta
          {mode === "assigned" && rule !== "MANUAL" ? " (con la asignación libre del taller completo)" : ""}. Los técnicos verán este orden en Mi día.
        </Notice>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setConfirm(false)}>Cancelar</Button>
          <Button variant="primary" icon={Shuffle} loading={busy} onClick={apply}>Guardar</Button>
        </div>
      </Modal>
    </div>
  );
}
