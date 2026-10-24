import { motion } from "framer-motion";
import { Clock, Search, Wrench } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { SkeletonCards } from "../components/Skeleton";
import { Card, ErrorState, InfoTip, PageHeader } from "../components/ui";
import { hours, money } from "../lib/format";
import { useApi } from "../lib/hooks";
import type { Service } from "../lib/types";

export default function Servicios() {
  const { data, error, loading, reload } = useApi<Service[]>("/api/services");
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("Todas");
  const navigate = useNavigate();
  const categories = useMemo(() => ["Todas", ...new Set((data ?? []).map((s) => s.category))], [data]);
  const list = (data ?? []).filter((s) =>
    (cat === "Todas" || s.category === cat) &&
    `${s.code} ${s.name} ${s.keywords}`.toLowerCase().includes(q.toLowerCase()));

  return (
    <div>
      <PageHeader icon={Wrench} title="Servicios" subtitle="Catálogo con tiempo estándar del estudio de tiempos"
        crumbs={[{ label: "Inicio", to: "/" }, { label: "Servicios" }]} />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative min-w-60 flex-1">
          <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
          <input className="field pl-9" placeholder="Buscar por nombre, código o síntoma…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Buscar servicio" />
        </div>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Categoría">
          {categories.map((c) => (
            <button key={c} type="button" onClick={() => setCat(c)} aria-pressed={cat === c}
              className={`cursor-pointer rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${cat === c ? "text-on-accent [background:var(--gradient-brand)]" : "bg-surface-muted text-secondary hover:text-text"}`}>
              {c}
            </button>
          ))}
        </div>
      </div>
      {error && <ErrorState message={error} onRetry={reload} />}
      {loading && <SkeletonCards n={8} />}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {list.map((s, i) => (
          <motion.div key={s.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: Math.min(i * 0.02, 0.4) }}>
            <Card onClick={() => navigate(`/servicios/${s.id}`)} className="h-full">
              <div className="flex items-start justify-between gap-2">
                <span className="rounded-md bg-accent-soft px-2 py-0.5 text-xs font-bold text-accent">{s.code}</span>
                <span className="text-xs text-muted">{s.category}</span>
              </div>
              <h3 className="mt-2 font-semibold text-text">{s.name}</h3>
              <div className="mt-3 flex items-center justify-between text-sm">
                <span className="inline-flex items-center gap-1 text-secondary">
                  <Clock size={14} aria-hidden /> {hours(s.std_hours)}
                  <InfoTip text="Tiempo estándar del servicio." formula="TS = TO × FC × (1 + suplementos)" />
                </span>
                <span className="text-muted">Refacciones {money(s.parts_cost)}</span>
              </div>
            </Card>
          </motion.div>
        ))}
      </div>
      {!loading && !list.length && <p className="py-10 text-center text-sm text-muted">Sin servicios para ese filtro.</p>}
    </div>
  );
}
