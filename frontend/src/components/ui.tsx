import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle, CheckCircle2, ChevronRight, CircleDot, Clock, Info, Loader2, PackageCheck, X, type LucideIcon,
} from "lucide-react";
import {
  createContext, useCallback, useContext, useEffect, useId, useRef, useState, type ButtonHTMLAttributes,
  type MouseEvent, type ReactNode,
} from "react";
import { Link } from "react-router-dom";

/* ---------- Tarjeta de vidrio con brillo que sigue al mouse ---------- */

function trackGlow(e: MouseEvent<HTMLElement>) {
  const r = e.currentTarget.getBoundingClientRect();
  e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`);
  e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`);
}

export function Card({ children, className = "", hover = false, onClick, title, actions, padded = true }: {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
  title?: ReactNode;
  actions?: ReactNode;
  padded?: boolean;
}) {
  const interactive = !!onClick;
  return (
    <section
      className={`glass rounded-lg ${hover || interactive ? "card-hover" : ""} ${interactive ? "cursor-pointer" : ""} ${padded ? "p-4 sm:p-5" : ""} ${className}`}
      onMouseMove={hover || interactive ? trackGlow : undefined}
      onClick={onClick}
      onKeyDown={interactive ? (e) => (e.key === "Enter" || e.key === " ") && onClick?.() : undefined}
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
    >
      {(title || actions) && (
        <header className="mb-3 flex flex-wrap items-center justify-between gap-2">
          {title && <h2 className="text-base font-semibold text-text">{title}</h2>}
          {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

/* ---------- Botón con microanimación ---------- */

type Variant = "primary" | "secondary" | "ghost" | "danger" | "gold";
const VARIANTS: Record<Variant, string> = {
  primary: "text-on-accent shadow-md hover:shadow-glow [background:var(--gradient-brand)]",
  secondary: "bg-surface-solid text-text border border-border-strong hover:border-accent hover:text-accent",
  ghost: "text-secondary hover:bg-surface-muted hover:text-text",
  danger: "bg-danger-soft text-danger border border-transparent hover:border-danger",
  gold: "text-[#1e2033] shadow-md hover:shadow-glow [background:var(--gold-vivid)]",
};

export function Button({ variant = "secondary", size = "md", icon: Icon, loading, children, className = "", ...rest }: {
  variant?: Variant;
  size?: "sm" | "md" | "lg" | "xl";
  icon?: LucideIcon;
  loading?: boolean;
} & Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onAnimationStart" | "onDrag" | "onDragStart" | "onDragEnd">) {
  const sizes = { sm: "h-8 px-3 text-xs gap-1.5", md: "h-10 px-4 text-sm gap-2", lg: "h-12 px-5 text-base gap-2", xl: "h-16 px-6 text-lg gap-3" };
  return (
    <motion.button
      whileHover={{ y: -1 }}
      whileTap={{ scale: 0.96 }}
      transition={{ type: "spring", stiffness: 500, damping: 30 }}
      className={`inline-flex cursor-pointer select-none items-center justify-center rounded-md font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-55 ${sizes[size]} ${VARIANTS[variant]} ${className}`}
      disabled={loading || rest.disabled}
      {...rest}
    >
      {loading ? <Loader2 className="animate-spin" size={size === "xl" ? 24 : 16} /> : Icon && <Icon size={size === "xl" ? 26 : 16} aria-hidden />}
      {children}
    </motion.button>
  );
}

/* ---------- Tooltip (globo informativo) accesible ---------- */

export function Tooltip({ content, children, side = "top" }: { content: ReactNode; children: ReactNode; side?: "top" | "bottom" }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
      aria-describedby={open ? id : undefined}
    >
      {children}
      <AnimatePresence>
        {open && (
          <motion.span
            id={id}
            role="tooltip"
            initial={{ opacity: 0, y: side === "top" ? 4 : -4, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className={`pointer-events-none absolute left-1/2 z-50 w-max max-w-[18rem] -translate-x-1/2 rounded-md border border-border-strong bg-surface-solid px-3 py-2 text-left text-xs font-normal leading-relaxed text-text shadow-lg ${side === "top" ? "bottom-full mb-2" : "top-full mt-2"}`}
          >
            {content}
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  );
}

/** Ícono "i" con globo: qué significa y cómo se calcula. */
export function InfoTip({ text, formula }: { text: ReactNode; formula?: string }) {
  return (
    <Tooltip content={<>{text}{formula && <span className="mt-1 block font-mono text-[11px] text-accent">{formula}</span>}</>}>
      <button type="button" className="inline-flex cursor-help rounded-full text-muted hover:text-accent" aria-label="Más información">
        <Info size={15} />
      </button>
    </Tooltip>
  );
}

/* ---------- Etiquetas de estado (ícono + texto, nunca solo color) ---------- */

const STATUS: Record<string, { cls: string; icon: LucideIcon; label?: string }> = {
  recibida: { cls: "bg-info-soft text-info", icon: CircleDot },
  "en proceso": { cls: "bg-purple-soft text-purple", icon: Clock },
  terminada: { cls: "bg-success-soft text-success", icon: CheckCircle2 },
  entregada: { cls: "bg-surface-muted text-secondary", icon: PackageCheck },
  vencida: { cls: "bg-danger-soft text-danger", icon: AlertTriangle },
  hoy: { cls: "bg-warning-soft text-warning", icon: Clock, label: "vence hoy" },
  próxima: { cls: "bg-info-soft text-info", icon: CircleDot, label: "próxima" },
  ok: { cls: "bg-success-soft text-success", icon: CheckCircle2, label: "ok" },
  reordenar: { cls: "bg-warning-soft text-warning", icon: AlertTriangle, label: "reordenar" },
  agotado: { cls: "bg-danger-soft text-danger", icon: AlertTriangle, label: "agotado" },
};

export function StatusBadge({ status }: { status: string }) {
  const s = STATUS[status] ?? { cls: "bg-surface-muted text-secondary", icon: CircleDot };
  const Icon = s.icon;
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${s.cls}`}>
      <Icon size={12} aria-hidden /> {s.label ?? status}
    </span>
  );
}

/* ---------- Encabezado de página y breadcrumbs ---------- */

export interface Crumb {
  label: string;
  to?: string;
  onClick?: () => void;
}

export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Ruta" className="mb-2 flex flex-wrap items-center gap-1 text-xs text-muted">
      {items.map((c, i) => (
        <span key={i} className="inline-flex items-center gap-1">
          {i > 0 && <ChevronRight size={12} aria-hidden />}
          {c.to ? (
            <Link to={c.to} className="hover:text-accent hover:underline">{c.label}</Link>
          ) : c.onClick ? (
            <button type="button" onClick={c.onClick} className="cursor-pointer hover:text-accent hover:underline">{c.label}</button>
          ) : (
            <span aria-current="page" className="font-medium text-secondary">{c.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}

export function PageHeader({ title, subtitle, crumbs, actions, icon: Icon }: {
  title: ReactNode;
  subtitle?: ReactNode;
  crumbs?: Crumb[];
  actions?: ReactNode;
  icon?: LucideIcon;
}) {
  return (
    <header className="mb-5">
      {crumbs && <Breadcrumbs items={crumbs} />}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex items-center gap-3">
          {Icon && (
            <span className="grid h-11 w-11 place-items-center rounded-md text-on-accent shadow-md [background:var(--gradient-brand)]">
              <Icon size={22} aria-hidden />
            </span>
          )}
          <div>
            <h1 className="text-xl font-bold tracking-tight text-text sm:text-2xl">{title}</h1>
            {subtitle && <p className="mt-0.5 text-sm text-secondary">{subtitle}</p>}
          </div>
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </header>
  );
}

/* ---------- Modal animado ---------- */

export function Modal({ open, onClose, title, subtitle, children, wide = false }: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    ref.current?.focus();
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-[60] flex items-end justify-center p-0 sm:items-center sm:p-6"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <div className="absolute inset-0 bg-black/35 backdrop-blur-sm" onClick={onClose} aria-hidden />
          <motion.div
            ref={ref}
            role="dialog"
            aria-modal="true"
            tabIndex={-1}
            initial={{ opacity: 0, y: 40, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 30, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 320, damping: 30 }}
            className={`glass relative max-h-[92vh] w-full overflow-y-auto rounded-t-xl bg-surface-solid p-5 outline-none sm:rounded-xl sm:p-6 ${wide ? "sm:max-w-4xl" : "sm:max-w-xl"}`}
          >
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-text">{title}</h2>
                {subtitle && <p className="mt-0.5 text-sm text-secondary">{subtitle}</p>}
              </div>
              <button type="button" onClick={onClose} className="cursor-pointer rounded-md p-1.5 text-muted hover:bg-surface-muted hover:text-text" aria-label="Cerrar">
                <X size={18} />
              </button>
            </div>
            {children}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* ---------- Estados vacíos, errores y avisos ---------- */

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 rounded-lg bg-danger-soft p-6 text-center text-danger">
      <AlertTriangle aria-hidden />
      <p className="text-sm">{message}</p>
      {onRetry && <Button size="sm" onClick={onRetry}>Reintentar</Button>}
    </div>
  );
}

export function Notice({ kind = "info", children }: { kind?: "info" | "warning" | "success" | "danger"; children: ReactNode }) {
  const map = {
    info: ["bg-info-soft text-info", Info],
    warning: ["bg-warning-soft text-warning", AlertTriangle],
    success: ["bg-success-soft text-success", CheckCircle2],
    danger: ["bg-danger-soft text-danger", AlertTriangle],
  } as const;
  const [cls, Icon] = map[kind];
  return (
    <div className={`flex items-start gap-2 rounded-md px-3 py-2.5 text-sm ${cls}`}>
      <Icon size={16} className="mt-0.5 shrink-0" aria-hidden />
      <div>{children}</div>
    </div>
  );
}

export function Segmented<T extends string>({ value, options, onChange, label }: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-md border border-border bg-surface-muted p-1">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={`relative cursor-pointer rounded-sm px-3 py-1.5 text-sm font-medium transition-colors ${value === o.value ? "text-text" : "text-muted hover:text-text"}`}
        >
          {value === o.value && (
            <motion.span layoutId={`seg-${label}`} className="absolute inset-0 rounded-sm bg-surface-solid shadow-sm" transition={{ type: "spring", stiffness: 500, damping: 35 }} />
          )}
          <span className="relative">{o.label}</span>
        </button>
      ))}
    </div>
  );
}

/* ---------- Toasts ---------- */

interface Toast {
  id: number;
  kind: "success" | "danger" | "info";
  text: string;
}
const ToastContext = createContext<(text: string, kind?: Toast["kind"]) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((text: string, kind: Toast["kind"] = "success") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, kind, text }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[80] flex w-[min(92vw,22rem)] flex-col gap-2" aria-live="polite">
        <AnimatePresence>
          {toasts.map((t) => (
            <motion.div key={t.id} layout initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 40 }}>
              <Notice kind={t.kind}>{t.text}</Notice>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
