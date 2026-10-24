import { ArrowLeft, Calculator, Save, Wrench } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Field, TextArea } from "../components/fields";
import { ThemedLoader } from "../components/loaders";
import { Table } from "../components/Table";
import { Button, Card, ErrorState, InfoTip, Notice, PageHeader, useToast } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { hours, money, num, pct } from "../lib/format";
import { useApi } from "../lib/hooks";
import type { Service } from "../lib/types";

interface Detail extends Service {
  parts: { code: string; name: string; qty: number; price: number; importe: number }[];
  stats: { veces_realizado: number; real_promedio_h: number | null };
}
interface StudyResult {
  promedio_min: number; normal_min: number; estandar_min: number; estandar_h: number;
  observaciones: number; observaciones_necesarias: number | null; suficientes: boolean;
}

function Metric({ label, value, tip, formula }: { label: string; value: string; tip: string; formula?: string }) {
  return (
    <div className="rounded-md bg-surface-muted p-3">
      <div className="flex items-center gap-1 text-xs text-secondary">{label}<InfoTip text={tip} formula={formula} /></div>
      <div className="mt-0.5 text-lg font-bold text-text tabular-nums">{value}</div>
    </div>
  );
}

export default function ServicioDetalle() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { can } = useAuth();
  const toast = useToast();
  const isAdmin = can("admin");
  const { data, error, loading, reload } = useApi<Detail>(`/api/services/${id}`);
  const [form, setForm] = useState({ name: "", category: "", observed_avg_min: 0, rating_factor: 1, allowance_pct: 0.15, steps: "" });
  const [obs, setObs] = useState("");
  const [conf, setConf] = useState(0.95);
  const [err, setErr] = useState(0.05);
  const [study, setStudy] = useState<StudyResult | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (data) setForm({ name: data.name, category: data.category, observed_avg_min: data.observed_avg_min, rating_factor: data.rating_factor, allowance_pct: data.allowance_pct, steps: data.steps.join("\n") });
  }, [data]);

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (loading || !data) return <ThemedLoader kind="gear" label="Abriendo ficha del servicio…" />;

  const tn = form.observed_avg_min * form.rating_factor;
  const ts = tn * (1 + form.allowance_pct);

  async function calc() {
    const values = obs.split(/[,;\s]+/).map(Number).filter((v) => v > 0);
    if (!values.length) return toast("Escribe al menos un tiempo observado.", "danger");
    try {
      setStudy(await api.post<StudyResult>("/api/time-study", { observations: values, rating_factor: form.rating_factor, allowance_pct: form.allowance_pct, confidence: conf, error: err }));
    } catch (e) {
      toast((e as Error).message, "danger");
    }
  }

  async function save() {
    setSaving(true);
    try {
      await api.put(`/api/services/${id}`, { ...form, steps: form.steps.split("\n") });
      toast("Servicio actualizado.");
      reload();
    } catch (e) {
      toast((e as Error).message, "danger");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <PageHeader icon={Wrench} title={`${data.code} · ${data.name}`} subtitle={data.category}
        crumbs={[{ label: "Servicios", to: "/servicios" }, { label: data.name }]}
        actions={<Button icon={ArrowLeft} variant="ghost" onClick={() => navigate("/servicios")}>Regresar</Button>} />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card title="Estudio de tiempos" className="lg:col-span-2">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric label="T. observado" value={`${num(form.observed_avg_min)} min`} tip="Promedio de los tiempos cronometrados." />
            <Metric label="T. normal" value={`${num(tn)} min`} tip="Ajusta el ritmo del operario observado." formula="TN = TO × factor de calificación" />
            <Metric label="T. estándar" value={`${num(ts)} min`} tip="Agrega suplementos por fatiga, necesidades y demoras." formula="TS = TN × (1 + % suplementos)" />
            <Metric label="Real promedio" value={hours(data.stats.real_promedio_h)} tip={`Promedio de ${data.stats.veces_realizado} registros reales en el taller.`} />
          </div>
          {isAdmin ? (
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <Field label="Nombre" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <Field label="Categoría" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
              <Field label="Tiempo observado promedio (min)" type="number" min={1} step="0.5" value={form.observed_avg_min} onChange={(e) => setForm({ ...form, observed_avg_min: Number(e.target.value) })} />
              <Field label="Factor de calificación" type="number" min={0.5} max={1.5} step="0.01" value={form.rating_factor} onChange={(e) => setForm({ ...form, rating_factor: Number(e.target.value) })} hint="1.00 = ritmo normal; 1.10 = 10 % más rápido." />
              <Field label="Suplementos (%)" type="number" min={0} max={100} step="1" value={Math.round(form.allowance_pct * 100)} onChange={(e) => setForm({ ...form, allowance_pct: Number(e.target.value) / 100 })} />
              <div className="sm:col-span-2"><TextArea label="Pasos (uno por línea)" value={form.steps} onChange={(e) => setForm({ ...form, steps: e.target.value })} /></div>
              <div className="sm:col-span-2"><Button variant="primary" icon={Save} loading={saving} onClick={save}>Guardar cambios</Button></div>
            </div>
          ) : (
            <p className="mt-3 text-xs text-muted">Solo el administrador puede modificar el catálogo.</p>
          )}
        </Card>

        <Card title={<span className="inline-flex items-center gap-2"><Calculator size={16} className="text-accent" aria-hidden />Calculadora de observaciones</span>}>
          <TextArea label="Tiempos observados (min), separados por coma" value={obs} onChange={(e) => setObs(e.target.value)} placeholder="38, 41, 36, 40, 39" />
          <div className="mt-3 grid grid-cols-2 gap-3">
            <Field label="Confianza (%)" type="number" min={80} max={99} value={Math.round(conf * 100)} onChange={(e) => setConf(Number(e.target.value) / 100)} />
            <Field label="Error aceptado (%)" type="number" min={1} max={20} value={Math.round(err * 100)} onChange={(e) => setErr(Number(e.target.value) / 100)} />
          </div>
          <Button className="mt-3 w-full" variant="secondary" icon={Calculator} onClick={calc}>Calcular</Button>
          {study && (
            <div className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-secondary">Promedio</span><b>{num(study.promedio_min)} min</b></div>
              <div className="flex justify-between"><span className="text-secondary">T. estándar</span><b>{num(study.estandar_min)} min ({hours(study.estandar_h)})</b></div>
              <div className="flex justify-between">
                <span className="inline-flex items-center gap-1 text-secondary">Observaciones necesarias<InfoTip text={`Con ${pct(conf)} de confianza y ±${pct(err)} de error.`} formula="n = (z · s / (e · x̄))²" /></span>
                <b>{study.observaciones_necesarias ?? "—"}</b>
              </div>
              <Notice kind={study.suficientes ? "success" : "warning"}>
                {study.observaciones_necesarias == null ? "Agrega al menos 2 observaciones." : study.suficientes ? `${study.observaciones} observaciones son suficientes.` : `Faltan ${study.observaciones_necesarias - study.observaciones} observaciones.`}
              </Notice>
              {isAdmin && <Button size="sm" variant="ghost" onClick={() => setForm({ ...form, observed_avg_min: Number(study.promedio_min.toFixed(1)) })}>Usar este promedio</Button>}
            </div>
          )}
        </Card>

        <Card title="Pasos">
          <ol className="space-y-2">
            {data.steps.map((s, i) => (
              <li key={i} className="flex gap-3 text-sm">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-xs font-bold text-on-accent [background:var(--gradient-brand)]">{i + 1}</span>{s}
              </li>
            ))}
          </ol>
        </Card>
        <Card title="Refacciones" className="lg:col-span-2">
          <Table rows={data.parts} rowKey={(p) => p.code} empty="Solo mano de obra."
            columns={[
              { key: "c", header: "Código", render: (p) => p.code },
              { key: "n", header: "Refacción", render: (p) => p.name },
              { key: "q", header: "Cant.", numeric: true, render: (p) => p.qty },
              { key: "p", header: "Precio", numeric: true, render: (p) => money(p.price) },
              { key: "i", header: "Importe", numeric: true, render: (p) => money(p.importe) },
            ]} />
          <p className="mt-2 text-right text-sm font-semibold text-text">Total refacciones: {money(data.parts_cost)}</p>
        </Card>
      </div>
    </div>
  );
}
