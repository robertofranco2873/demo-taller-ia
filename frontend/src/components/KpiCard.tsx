import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import type { LucideIcon } from "lucide-react";
import type { MouseEvent, ReactNode } from "react";
import { useCountUp } from "../lib/hooks";
import { InfoTip } from "./ui";

/** Tarjeta KPI: inclinación 3D leve, brillo, número animado y globo con la fórmula. */
export function KpiCard({ label, value, format, icon: Icon, hint, formula, sub, onClick, accent = "purple" }: {
  label: string;
  value: number | null | undefined;
  format: (v: number) => string;
  icon: LucideIcon;
  hint: string;
  formula?: string;
  sub?: ReactNode;
  onClick?: () => void;
  accent?: "purple" | "blue" | "gold";
}) {
  const reduced = useReducedMotion();
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotX = useSpring(useTransform(y, [-0.5, 0.5], [6, -6]), { stiffness: 220, damping: 18 });
  const rotY = useSpring(useTransform(x, [-0.5, 0.5], [-8, 8]), { stiffness: 220, damping: 18 });
  const shown = useCountUp(value);

  function onMove(e: MouseEvent<HTMLDivElement>) {
    const r = e.currentTarget.getBoundingClientRect();
    x.set((e.clientX - r.left) / r.width - 0.5);
    y.set((e.clientY - r.top) / r.height - 0.5);
    e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`);
    e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`);
  }
  function onLeave() {
    x.set(0);
    y.set(0);
  }
  const tone = { purple: "bg-purple-soft text-purple", blue: "bg-blue-soft text-blue", gold: "bg-gold-soft text-gold" }[accent];

  return (
    <div style={{ perspective: 800 }}>
      <motion.div
        onMouseMove={onMove}
        onMouseLeave={onLeave}
        onClick={onClick}
        onKeyDown={(e) => onClick && (e.key === "Enter" || e.key === " ") && onClick()}
        role={onClick ? "button" : undefined}
        tabIndex={onClick ? 0 : undefined}
        aria-label={onClick ? `${label}: ver detalle` : undefined}
        style={reduced ? undefined : { rotateX: rotX, rotateY: rotY, transformStyle: "preserve-3d" }}
        whileTap={onClick ? { scale: 0.98 } : undefined}
        className={`glass card-hover rounded-lg p-4 ${onClick ? "cursor-pointer" : ""}`}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-1.5 text-sm font-medium text-secondary">
            {label}
            <span onClick={(e) => e.stopPropagation()}>
              <InfoTip text={hint} formula={formula} />
            </span>
          </div>
          <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-md ${tone}`} style={{ transform: "translateZ(20px)" }}>
            <Icon size={18} aria-hidden />
          </span>
        </div>
        <div className="mt-2 text-2xl font-bold tracking-tight text-text tabular-nums sm:text-[1.7rem]" style={{ transform: "translateZ(30px)" }}>
          {shown == null ? "—" : format(shown)}
        </div>
        {sub && <div className="mt-1 text-xs text-muted">{sub}</div>}
      </motion.div>
    </div>
  );
}
