import { ListOrdered, Shuffle, Trophy } from "lucide-react";
import { useState } from "react";
import { Chart } from "../components/Chart";
import { SelectField } from "../components/fields";
import { Table } from "../components/Table";
import { Button, Card, ErrorState, InfoTip, Modal, Notice, PageHeader, Segmented, StatusBadge, useToast } from "../components/ui";
import { api } from "../lib/api";
import { useChartColors } from "../lib/chartTheme";
import { ganttOption } from "../lib/charts";
import { dateTime, num } from "../lib/format";
import { useApi } from "../lib/hooks";
import type { Technician } from "../lib/types";

type Rule = "FIFO" | "SPT" | "EDD";
type Mode = "assigned" | "shop" | "technician";
interface Comparison { regla: Rule; flujo_promedio_h: number; retraso_promedio_h: number; ordenes_tarde: number; makespan_h: number }
interface SchedRow { posicion: number; orden: string; recurso: string; bahia: string; proceso_h: number; entrega_h: number; inicio: string; fin: string; flujo_h: number; retraso_h: number; tarde: boolean }
interface Seq { jobs: number; hours: number; now: string; rules: Record<Rule, string>; comparison: Comparison[]; schedule: SchedRow[] }

export default function Secuenciacion() {
  const c = useChartColors();
  const toast = useToast();
  const [rule, setRule] = useState<Rule>("EDD");
  const [mode, setMode] = useState<Mode>("assigned");
  const [tech, setTech] = useState(1);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const techs = useApi<Technician[]>("/api/technicians");
  const { data, error, loading, reload } = useApi<Seq>("/api/sequencing", { rule, mode, technician_id: mode === "technician" ? tech : null });
  if (error) return <ErrorState message={error} onRetry={reload} />;

  const best = (k: keyof Comparison) => data?.comparison.length ? data.comparison.reduce((a, b) => (Number(b[k]) < Number(a[k]) ? b : a)).regla : null;
  const resources = mode === "technician" ? (techs.data ?? []).filter((t) => t.id === tech).map((t) => t.name) : (techs.data ?? []).map((t) => t.name);

  async function apply() {
    setBusy(true);
    try {
      const r = await api.post<{ updated: number }>("/api/sequencing/apply", { rule, mode: mode === "assigned" ? "shop" : mode, technician_id: mode === "technician" ? tech : null });
      toast(`Reasignación aplicada a ${r.updated} órdenes (técnico, bahía y fecha).`);
      setConfirm(false);
      reload();
    } catch (e) {
      toast((e as Error).message, "danger");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader icon={ListOrdered} title="Secuenciación de órdenes pendientes" subtitle="Reglas FIFO, SPT y EDD con técnicos y bahías como recursos"
        crumbs={[{ label: "Análisis" }, { label: "Secuenciación" }]}
        actions={<Button variant="gold" icon={Shuffle} onClick={() => setConfirm(true)} disabled={!data?.jobs}>Reasignar con esta propuesta</Button>} />
      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <Segmented label="Alcance" value={mode} onChange={setMode} options={[
            { value: "assigned", label: "Respetar asignación" }, { value: "shop", label: "Taller completo" }, { value: "technician", label: "Por técnico" },
          ]} />
          {mode === "technician" && (
            <div className="w-64"><SelectField label="Técnico" value={tech} onChange={(e) => setTech(Number(e.target.value))}>{techs.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</SelectField></div>
          )}
          <InfoTip text="Cada orden usa un técnico y una bahía. Inicio = cuando ambos están libres. «Taller completo» asigna al técnico que se libera primero." formula="Flujo = fin · Retraso = máx(0, fin − compromiso)" />
        </div>
        {data && <p className="mt-3 text-xs text-muted">{data.jobs} órdenes · {num(data.hours)} h estándar · inicio {dateTime(data.now)} · tiempos en horas laborables (L-S, 8 h)</p>}
      </Card>

      <Card className="mt-4" title="Comparativa de reglas">
        <Table rows={data?.comparison} loading={loading} rowKey={(r) => r.regla} onRowClick={(r) => setRule(r.regla)} columns={[
          { key: "r", header: "Regla", render: (r) => <span className="inline-flex items-center gap-2 font-semibold">{r.regla === rule && <span className="h-2 w-2 rounded-full [background:var(--gold-vivid)]" aria-label="seleccionada" />}{r.regla}<span className="hidden text-xs font-normal text-muted md:inline">{data?.rules[r.regla]}</span></span> },
          { key: "f", header: "Flujo prom.", numeric: true, render: (r) => <span className={best("flujo_promedio_h") === r.regla ? "font-bold text-success" : ""}>{best("flujo_promedio_h") === r.regla && <Trophy size={12} className="mr-1 inline" aria-label="mejor" />}{num(r.flujo_promedio_h)} h</span> },
          { key: "t", header: "Retraso prom.", numeric: true, render: (r) => <span className={best("retraso_promedio_h") === r.regla ? "font-bold text-success" : ""}>{best("retraso_promedio_h") === r.regla && <Trophy size={12} className="mr-1 inline" aria-label="mejor" />}{num(r.retraso_promedio_h)} h</span> },
          { key: "l", header: "Tarde", numeric: true, render: (r) => <span className={best("ordenes_tarde") === r.regla ? "font-bold text-success" : ""}>{r.ordenes_tarde}</span> },
          { key: "m", header: "Makespan", numeric: true, render: (r) => `${num(r.makespan_h)} h` },
        ]} />
        <p className="mt-2 text-xs text-muted">Clic en una regla para verla en el Gantt. Las órdenes ya vencidas cuentan como tarde con cualquier regla.</p>
      </Card>

      <Card className="mt-4" title={`Diagrama de Gantt · ${rule}`} actions={<Segmented label="Regla" value={rule} onChange={setRule} options={[{ value: "FIFO", label: "FIFO" }, { value: "SPT", label: "SPT" }, { value: "EDD", label: "EDD" }]} />}>
        <Chart loading={loading || !data} height={Math.max(260, resources.length * 80 + 90)} ariaLabel={`Diagrama de Gantt regla ${rule}`}
          option={ganttOption(c, (data?.schedule ?? []).map((s) => ({ resource: s.recurso, folio: s.orden, start: new Date(s.inicio).getTime(), end: new Date(s.fin).getTime(), late: s.tarde, bay: s.bahia })), resources)} />
        <p className="mt-1 text-xs text-muted">Azul = a tiempo · Rojo = tarde. Arrastra o usa la rueda para hacer zoom.</p>
      </Card>

      <Card className="mt-4" title="Secuencia propuesta">
        <Table rows={data?.schedule} loading={loading} rowKey={(s) => s.orden} maxHeight={420} columns={[
          { key: "p", header: "#", numeric: true, render: (s) => s.posicion },
          { key: "o", header: "Orden", render: (s) => s.orden },
          { key: "r", header: "Técnico", render: (s) => s.recurso },
          { key: "b", header: "Bahía", hideOnMobile: true, render: (s) => s.bahia },
          { key: "i", header: "Inicio", render: (s) => dateTime(s.inicio) },
          { key: "f", header: "Fin", hideOnMobile: true, render: (s) => dateTime(s.fin) },
          { key: "x", header: "Retraso", numeric: true, render: (s) => (s.tarde
            ? <span className="inline-flex items-center gap-1.5 font-medium text-danger">{num(s.retraso_h)} h <StatusBadge status="vencida" /></span>
            : <span className="text-success">a tiempo</span>) },
        ]} />
      </Card>

      <Modal open={confirm} onClose={() => setConfirm(false)} title="¿Reasignar órdenes?" subtitle={`Regla ${rule}`}>
        <Notice kind="warning">Se actualizará el técnico, la bahía y la fecha programada de las {data?.jobs} órdenes pendientes según la propuesta {mode === "assigned" ? "(se usará la asignación libre del taller completo)" : ""}.</Notice>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setConfirm(false)}>Cancelar</Button>
          <Button variant="primary" icon={Shuffle} loading={busy} onClick={apply}>Aplicar</Button>
        </div>
      </Modal>
    </div>
  );
}
