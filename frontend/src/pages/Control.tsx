import { LineChart } from "lucide-react";
import { useEffect, useState } from "react";
import { Chart } from "../components/Chart";
import { SelectField } from "../components/fields";
import { Table } from "../components/Table";
import { Card, ErrorState, InfoTip, Notice, PageHeader, Segmented } from "../components/ui";
import { useChartColors } from "../lib/chartTheme";
import { controlOption } from "../lib/charts";
import { hours, pct } from "../lib/format";
import { useApi } from "../lib/hooks";
import type { Technician } from "../lib/types";

interface Point { n: number; valor: number; fuera_de_limites: boolean; racha: boolean; folio: string; technician: string; fecha: string }
interface Individuals { points: Point[]; limits: { lc: number; lsc: number; lic: number; sigma: number }; std_hours: number; signals: number }
interface XbarR {
  subgroups: { subgrupo: number; xbar: number; rango: number; xbar_fuera: boolean; rango_fuera: boolean }[];
  limits: { xbar: { lc: number; lsc: number; lic: number }; r: { lc: number; lsc: number; lic: number }; n: number; a2: number; d3: number; d4: number };
}

export default function Control() {
  const c = useChartColors();
  const services = useApi<{ service_id: number; service_name: string; registros: number }[]>("/api/spc/services");
  const techs = useApi<Technician[]>("/api/technicians");
  const [sid, setSid] = useState<number | null>(null);
  const [tech, setTech] = useState<number | null>(null);
  const [kind, setKind] = useState<"ind" | "xr">("ind");
  const [n, setN] = useState(5);
  useEffect(() => {
    if (services.data?.length && sid === null) setSid(services.data[0].service_id);
  }, [services.data, sid]);
  const ind = useApi<Individuals>(sid && kind === "ind" ? "/api/spc/individuals" : null, { service_id: sid, technician_id: tech, last_n: 60 });
  const xr = useApi<XbarR>(sid && kind === "xr" ? "/api/spc/xbar-r" : null, { service_id: sid, technician_id: tech, subgroup: n, last_n: 100 });

  return (
    <div>
      <PageHeader icon={LineChart} title="Control estadístico de tiempos reales" subtitle="Detecta variación anormal (causas asignables)"
        crumbs={[{ label: "Análisis" }, { label: "Control estadístico" }]} />
      <Card>
        <div className="grid gap-3 md:grid-cols-4">
          <div className="md:col-span-2">
            <SelectField label="Servicio" value={sid ?? ""} onChange={(e) => setSid(Number(e.target.value))}>
              {services.data?.map((s) => <option key={s.service_id} value={s.service_id}>{s.service_name} ({s.registros} registros)</option>)}
            </SelectField>
          </div>
          <SelectField label="Técnico" value={tech ?? ""} onChange={(e) => setTech(e.target.value ? Number(e.target.value) : null)}>
            <option value="">Todos</option>
            {techs.data?.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </SelectField>
          {kind === "xr" && (
            <SelectField label="Tamaño de subgrupo (n)" value={n} onChange={(e) => setN(Number(e.target.value))}>
              {[2, 3, 4, 5, 6, 8, 10].map((v) => <option key={v} value={v}>{v}</option>)}
            </SelectField>
          )}
        </div>
        <div className="mt-3">
          <Segmented label="Tipo de gráfica" value={kind} onChange={setKind} options={[{ value: "ind", label: "X̄ individuales ±3σ" }, { value: "xr", label: "X̄-R por subgrupos" }]} />
        </div>
      </Card>

      {kind === "ind" && (ind.error ? <div className="mt-4"><ErrorState message={ind.error} /></div> : (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-5">
            {[["Media (LC)", ind.data && hours(ind.data.limits.lc)], ["σ", ind.data && hours(ind.data.limits.sigma)], ["LSC", ind.data && hours(ind.data.limits.lsc)],
              ["LIC", ind.data && hours(ind.data.limits.lic)], ["Media vs. estándar", ind.data && pct(ind.data.limits.lc / ind.data.std_hours - 1)]].map(([l, v]) => (
              <Card key={l as string} hover padded={false} className="p-3"><div className="text-xs text-secondary">{l}</div><div className="text-lg font-bold text-text">{v ?? "…"}</div></Card>
            ))}
          </div>
          <Card className="mt-4" title={<span className="inline-flex items-center gap-1">Gráfica X̄ de individuales<InfoTip text="σ = desviación estándar muestral. Señal: punto fuera de límites o racha de 7 del mismo lado de la media." formula="LSC/LIC = x̄ ± 3σ (LIC ≥ 0)" /></span>}>
            <Chart loading={ind.loading || !ind.data} height={360} ariaLabel="Gráfica de control de individuales" option={controlOption(c, {
              values: ind.data?.points.map((p) => p.valor) ?? [], signals: ind.data?.points.map((p) => p.fuera_de_limites || p.racha) ?? [],
              labels: ind.data?.points.map((p) => `${p.fecha} · ${p.folio} · ${p.technician}`) ?? [], limits: ind.data?.limits ?? { lc: 0, lsc: 0, lic: 0 }, name: "Horas reales",
            })} />
            {ind.data && (ind.data.signals ? (
              <>
                <Notice kind="danger">{ind.data.signals} punto(s) con variación anormal. Investiga causa asignable (retrabajo, refacción incorrecta, herramienta).</Notice>
                <div className="mt-3"><Table rows={ind.data.points.filter((p) => p.fuera_de_limites || p.racha)} rowKey={(p) => p.n} columns={[
                  { key: "n", header: "Muestra", numeric: true, render: (p) => p.n }, { key: "f", header: "Fecha", render: (p) => p.fecha },
                  { key: "o", header: "Folio", render: (p) => p.folio }, { key: "t", header: "Técnico", render: (p) => p.technician },
                  { key: "v", header: "Horas", numeric: true, render: (p) => hours(p.valor) },
                  { key: "s", header: "Señal", render: (p) => (p.fuera_de_limites ? "Fuera de límites" : "Racha") },
                ]} /></div>
              </>
            ) : <Notice kind="success">Proceso bajo control: sin señales de variación anormal.</Notice>)}
          </Card>
        </>
      ))}

      {kind === "xr" && (xr.error ? <div className="mt-4"><ErrorState message={xr.error} /></div> : (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Card title={<span className="inline-flex items-center gap-1">Gráfica X̄ (medias)<InfoTip text={`Subgrupos consecutivos de ${n}. A2 = ${xr.data?.limits.a2 ?? "…"}`} formula="LSC/LIC = X̿ ± A2 · R̄" /></span>}>
            <Chart loading={xr.loading || !xr.data} height={300} ariaLabel="Gráfica X barra" option={controlOption(c, {
              values: xr.data?.subgroups.map((s) => s.xbar) ?? [], signals: xr.data?.subgroups.map((s) => s.xbar_fuera) ?? [],
              labels: xr.data?.subgroups.map((s) => `Subgrupo ${s.subgrupo}`) ?? [], limits: xr.data?.limits.xbar ?? { lc: 0, lsc: 0, lic: 0 }, name: "X̄",
            })} />
          </Card>
          <Card title={<span className="inline-flex items-center gap-1">Gráfica R (rangos)<InfoTip text={`D3 = ${xr.data?.limits.d3 ?? "…"}, D4 = ${xr.data?.limits.d4 ?? "…"}`} formula="LSC = D4 · R̄ · LIC = D3 · R̄" /></span>}>
            <Chart loading={xr.loading || !xr.data} height={300} ariaLabel="Gráfica de rangos" option={controlOption(c, {
              values: xr.data?.subgroups.map((s) => s.rango) ?? [], signals: xr.data?.subgroups.map((s) => s.rango_fuera) ?? [],
              labels: xr.data?.subgroups.map((s) => `Subgrupo ${s.subgrupo}`) ?? [], limits: xr.data?.limits.r ?? { lc: 0, lsc: 0, lic: 0 }, name: "R",
            })} />
          </Card>
        </div>
      ))}
    </div>
  );
}
