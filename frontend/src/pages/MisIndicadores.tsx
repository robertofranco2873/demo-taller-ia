import { Award, CheckCheck, Gauge, Hourglass, TrendingUp } from "lucide-react";
import { useEffect } from "react";
import { Chart } from "../components/Chart";
import { KpiCard } from "../components/KpiCard";
import { ThemedLoader } from "../components/loaders";
import { Table } from "../components/Table";
import { Card, ErrorState, Notice, PageHeader } from "../components/ui";
import { celebrateGoalOnce } from "../lib/celebrate";
import { useChartColors } from "../lib/chartTheme";
import { barOption, trendOption } from "../lib/charts";
import { date, month, pct } from "../lib/format";
import { useApi } from "../lib/hooks";

interface Indicators {
  technician: string; eficiencia: number | null; utilizacion: number; horas_reales: number; ordenes_cerradas: number;
  ordenes_pendientes: number; tendencia: { mes: string; eficiencia: number }[];
  servicios_frecuentes: { service_name: string; veces: number }[]; semanal: { semana: string; terminadas: number; eficiencia: number }[];
  meta: number;
  regla_eficiencia: string;
}

export default function MisIndicadores() {
  const { data, error, loading, reload } = useApi<Indicators>("/api/me/indicators");
  const c = useChartColors();
  const reached = !!data && data.eficiencia != null && data.eficiencia >= data.meta;

  useEffect(() => {
    if (reached) celebrateGoalOnce("personal");
  }, [reached]);

  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (loading || !data) return <ThemedLoader kind="piston" label="Calculando tus indicadores…" />;

  return (
    <div>
      <PageHeader icon={TrendingUp} title="Mis indicadores" subtitle={data.technician} />
      {reached ? (
        <Notice kind="success"><Award size={14} className="mr-1 inline" aria-hidden />¡Estás arriba de la meta de eficiencia ({pct(data.meta)})!</Notice>
      ) : (
        <Notice kind="info">Meta de eficiencia del taller: {pct(data.meta)}. Eficiencia = tiempo estándar ÷ tiempo real.</Notice>
      )}
      <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Eficiencia" value={data.eficiencia} format={(v) => pct(v)} icon={Gauge} accent="purple"
          hint={`Más de 100 % = terminas más rápido que el tiempo estándar. ${data.regla_eficiencia}`} formula="Σ horas estándar ÷ Σ horas reales (tope 200 %)" />
        <KpiCard label="Órdenes terminadas" value={data.ordenes_cerradas} format={(v) => Math.round(v).toString()} icon={CheckCheck} accent="blue"
          hint="Órdenes que terminaste o ya se entregaron." />
        <KpiCard label="Utilización" value={data.utilizacion} format={(v) => pct(v)} icon={Hourglass} accent="gold"
          hint="Horas reales trabajadas entre horas disponibles (6 días × 8 h por semana)." formula="Σ horas reales ÷ horas disponibles" />
        <KpiCard label="Pendientes" value={data.ordenes_pendientes} format={(v) => Math.round(v).toString()} icon={Award} accent="purple"
          hint="Tus órdenes recibidas o en proceso." />
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card title="Tendencia mensual de eficiencia">
          <Chart ariaLabel="Tendencia mensual de eficiencia" option={trendOption(c, {
            categories: data.tendencia.map((t) => month(t.mes)), values: data.tendencia.map((t) => t.eficiencia),
            name: "Eficiencia", format: (v) => pct(v), goal: { value: data.meta, label: `Meta ${pct(data.meta)}` }, area: true,
          })} />
        </Card>
        <Card title="Órdenes terminadas por semana">
          <Chart ariaLabel="Órdenes terminadas por semana" option={barOption(c, {
            categories: data.semanal.map((s) => date(s.semana).slice(0, 6)), values: data.semanal.map((s) => s.terminadas),
            name: "Terminadas", format: (v) => String(Math.round(v)), labels: true,
          })} />
        </Card>
      </div>
      <Card title="Servicios que más realizas" className="mt-4">
        <Table rows={data.servicios_frecuentes} rowKey={(r) => r.service_name}
          columns={[{ key: "s", header: "Servicio", render: (r) => r.service_name }, { key: "v", header: "Veces", numeric: true, render: (r) => r.veces }]} />
      </Card>
    </div>
  );
}
