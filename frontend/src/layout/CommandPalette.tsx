import { AnimatePresence, motion } from "framer-motion";
import { ClipboardList, CornerDownLeft, LayoutGrid, Search, User, Wrench, type LucideIcon } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useDebounced } from "../lib/hooks";
import { modulesFor } from "../lib/modules";

interface Result {
  type: "modulo" | "servicio" | "orden" | "tecnico";
  id: string | number;
  title: string;
  subtitle: string;
  path: string;
}

const TYPE: Record<Result["type"], { label: string; icon: LucideIcon }> = {
  modulo: { label: "Módulos", icon: LayoutGrid },
  servicio: { label: "Servicios", icon: Wrench },
  orden: { label: "Órdenes", icon: ClipboardList },
  tecnico: { label: "Técnicos", icon: User },
};

/** Paleta de comandos (Ctrl+K): módulos (local, por rol) + servicios, órdenes y técnicos (API). */
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [remote, setRemote] = useState<Result[]>([]);
  const [active, setActive] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const dq = useDebounced(q, 200);

  useEffect(() => {
    if (open) {
      setQ("");
      setActive(0);
      setTimeout(() => input.current?.focus(), 30);
    }
  }, [open]);

  useEffect(() => {
    if (!open || dq.trim().length < 2) {
      setRemote([]);
      return;
    }
    let alive = true;
    api.get<Result[]>("/api/search", { q: dq }).then((r) => alive && setRemote(r.filter((x) => x.type !== "modulo"))).catch(() => {});
    return () => {
      alive = false;
    };
  }, [dq, open]);

  const results = useMemo(() => {
    const ql = q.trim().toLowerCase();
    const mods: Result[] = modulesFor(user?.role)
      .filter((m) => !ql || m.title.toLowerCase().includes(ql) || m.description.toLowerCase().includes(ql))
      .map((m) => ({ type: "modulo", id: m.key, title: m.title, subtitle: m.description, path: m.path }));
    return [...mods, ...remote];
  }, [q, remote, user]);

  function go(r: Result) {
    navigate(r.path);
    onClose();
  }

  function onKey(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter" && results[active]) {
      go(results[active]);
    } else if (e.key === "Escape") {
      onClose();
    }
  }

  let lastType = "";
  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-[70] flex items-start justify-center p-3 pt-[10vh]" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} aria-hidden />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Buscar"
            initial={{ y: -16, scale: 0.98 }}
            animate={{ y: 0, scale: 1 }}
            exit={{ y: -10, opacity: 0 }}
            className="glass relative w-full max-w-xl overflow-hidden rounded-xl bg-surface-solid"
          >
            <div className="flex items-center gap-2 border-b border-border px-4">
              <Search size={18} className="text-muted" aria-hidden />
              <input
                ref={input}
                value={q}
                onChange={(e) => {
                  setQ(e.target.value);
                  setActive(0);
                }}
                onKeyDown={onKey}
                placeholder="Busca módulos, servicios, órdenes o técnicos…"
                className="h-14 w-full bg-transparent text-base text-text outline-none placeholder:text-muted"
                aria-label="Buscar"
                role="combobox"
                aria-expanded
                aria-controls="cmd-results"
                aria-activedescendant={results[active] ? `cmd-${active}` : undefined}
              />
              <kbd className="hidden rounded border border-border px-1.5 text-xs text-muted sm:block">Esc</kbd>
            </div>
            <ul id="cmd-results" role="listbox" className="max-h-[55vh] overflow-y-auto p-2">
              {results.length === 0 && <li className="p-6 text-center text-sm text-muted">Sin resultados para “{q}”.</li>}
              {results.map((r, i) => {
                const header = r.type !== lastType;
                lastType = r.type;
                const Icon = TYPE[r.type].icon;
                return (
                  <li key={`${r.type}-${r.id}`} role="presentation">
                    {header && <div className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-muted">{TYPE[r.type].label}</div>}
                    <button
                      id={`cmd-${i}`}
                      role="option"
                      aria-selected={i === active}
                      onMouseEnter={() => setActive(i)}
                      onClick={() => go(r)}
                      className={`flex w-full cursor-pointer items-center gap-3 rounded-md px-3 py-2 text-left ${i === active ? "bg-accent-soft" : ""}`}
                    >
                      <Icon size={16} className="shrink-0 text-accent" aria-hidden />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-text">{r.title}</span>
                        <span className="block truncate text-xs text-muted">{r.subtitle}</span>
                      </span>
                      {i === active && <CornerDownLeft size={14} className="text-muted" aria-hidden />}
                    </button>
                  </li>
                );
              })}
            </ul>
            <div className="flex gap-4 border-t border-border px-4 py-2 text-[11px] text-muted">
              <span>↑↓ moverse</span>
              <span>Enter abrir</span>
              <span>Ctrl+K abrir/cerrar</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
