import { AnimatePresence, motion } from "framer-motion";
import { Bell, ChevronDown, LogOut, Menu, Moon, Search, Sun, X } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { Logo, LogoIcon } from "../components/Logo";
import { Tooltip } from "../components/ui";
import { useAuth } from "../lib/auth";
import { useApi } from "../lib/hooks";
import { AREAS, HOME_BY_ROLE, ROLE_LABEL, modulesFor, type Module } from "../lib/modules";
import { useTheme } from "../lib/theme";

interface Notification {
  level: "critical" | "warning" | "info";
  title: string;
  detail: string;
  path: string;
}

function useOutside(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && close();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, close]);
  return ref;
}

function Dropdown({ label, children, align = "left", icon, ariaLabel, badge }: {
  label?: ReactNode;
  children: (close: () => void) => ReactNode;
  align?: "left" | "right";
  icon?: ReactNode;
  ariaLabel?: string;
  badge?: number;
}) {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  const ref = useOutside(open, close);
  const location = useLocation();
  useEffect(close, [location.pathname]);
  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={ariaLabel}
        className={`relative inline-flex h-10 cursor-pointer items-center gap-1.5 rounded-md px-3 text-sm font-medium transition-colors hover:bg-surface-muted ${open ? "bg-surface-muted text-text" : "text-secondary"}`}
      >
        {icon}
        {label}
        {label && <ChevronDown size={14} className={`transition-transform ${open ? "rotate-180" : ""}`} aria-hidden />}
        {!!badge && (
          <span className="absolute -right-0.5 -top-0.5 grid h-5 min-w-5 place-items-center rounded-full px-1 text-[11px] font-bold text-[#1e2033] [background:var(--gold-vivid)]">
            {badge}
          </span>
        )}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            role="menu"
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.16 }}
            className={`glass absolute top-full z-50 mt-2 min-w-[16rem] rounded-lg bg-surface-solid p-2 ${align === "right" ? "right-0" : "left-0"}`}
          >
            {children(close)}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function ModuleLink({ m, onClick }: { m: Module; onClick?: () => void }) {
  const Icon = m.icon;
  return (
    <NavLink
      to={m.path}
      onClick={onClick}
      role="menuitem"
      className={({ isActive }) => `flex items-center gap-3 rounded-md px-3 py-2 transition-colors hover:bg-accent-soft ${isActive ? "bg-accent-soft" : ""}`}
    >
      <Icon size={18} className="shrink-0 text-accent" aria-hidden />
      <span>
        <span className="block text-sm font-medium text-text">{m.title}</span>
        <span className="block text-xs text-muted">{m.description}</span>
      </span>
    </NavLink>
  );
}

export function TopBar({ onSearch }: { onSearch: () => void }) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const [drawer, setDrawer] = useState(false);
  const location = useLocation();
  const { data: notes } = useApi<Notification[]>(user ? "/api/notifications" : null, { p: location.pathname });
  useEffect(() => setDrawer(false), [location.pathname]);
  if (!user) return null;

  const mods = modulesFor(user.role);
  const areas = AREAS.filter((a) => mods.some((m) => m.area === a));
  const levelCls = { critical: "text-danger", warning: "text-warning", info: "text-info" };

  return (
    <>
      <div className="bg-gold-soft py-1 text-center text-[11px] font-medium text-gold">
        DEMO · AutoServicio Demo no es un negocio real · todos los datos son ficticios
      </div>
      <header className="glass sticky top-0 z-40 rounded-none border-x-0 border-t-0">
        <div className="mx-auto flex h-16 max-w-7xl items-center gap-2 px-3 sm:px-5">
          <button type="button" className="cursor-pointer rounded-md p-2 text-secondary hover:bg-surface-muted lg:hidden" onClick={() => setDrawer(true)} aria-label="Abrir menú">
            <Menu size={20} />
          </button>
          <Link to={HOME_BY_ROLE[user.role]} className="mr-2 shrink-0" aria-label="Inicio">
            <span className="hidden sm:inline"><Logo size={34} /></span>
            <span className="sm:hidden"><LogoIcon size={32} /></span>
          </Link>

          <nav aria-label="Menú principal" className="hidden items-center gap-1 lg:flex">
            {areas.map((area) => (
              <Dropdown key={area} label={area}>
                {(close) => mods.filter((m) => m.area === area).map((m) => <ModuleLink key={m.key} m={m} onClick={close} />)}
              </Dropdown>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-1">
            <button
              type="button"
              onClick={onSearch}
              className="hidden h-10 cursor-pointer items-center gap-2 rounded-md border border-border bg-surface-muted px-3 text-sm text-muted transition-colors hover:border-accent hover:text-text md:inline-flex"
            >
              <Search size={16} aria-hidden /> Buscar…
              <kbd className="rounded border border-border px-1.5 text-[11px]">Ctrl K</kbd>
            </button>
            <button type="button" onClick={onSearch} className="cursor-pointer rounded-md p-2.5 text-secondary hover:bg-surface-muted md:hidden" aria-label="Buscar">
              <Search size={18} />
            </button>

            <Dropdown align="right" icon={<Bell size={18} />} ariaLabel="Notificaciones" badge={notes?.length}>
              {(close) => (
                <div className="w-[min(85vw,20rem)]">
                  <div className="px-3 pb-2 pt-1 text-xs font-semibold uppercase tracking-wide text-muted">Notificaciones</div>
                  {!notes?.length && <p className="px-3 py-4 text-sm text-muted">Todo en orden. 🎉</p>}
                  {notes?.map((n, i) => (
                    <button key={i} type="button" onClick={() => { navigate(n.path); close(); }} className="block w-full cursor-pointer rounded-md px-3 py-2 text-left hover:bg-accent-soft">
                      <span className={`block text-sm font-medium ${levelCls[n.level]}`}>{n.title}</span>
                      <span className="block text-xs text-muted">{n.detail}</span>
                    </button>
                  ))}
                </div>
              )}
            </Dropdown>

            <Tooltip content={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"} side="bottom">
              <motion.button type="button" whileTap={{ rotate: 90, scale: 0.9 }} onClick={toggle} className="cursor-pointer rounded-md p-2.5 text-secondary hover:bg-surface-muted" aria-label="Cambiar tema">
                {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
              </motion.button>
            </Tooltip>

            <Dropdown
              align="right"
              ariaLabel="Menú de usuario"
              icon={
                <span className="grid h-8 w-8 place-items-center rounded-full text-sm font-bold text-on-accent [background:var(--gradient-brand)]">
                  {user.name.charAt(0)}
                </span>
              }
            >
              {() => (
                <div>
                  <div className="px-3 py-2">
                    <div className="text-sm font-semibold text-text">{user.name}</div>
                    <div className="text-xs text-muted">{ROLE_LABEL[user.role]} · @{user.username}</div>
                  </div>
                  <hr className="my-1 border-border" />
                  <button type="button" role="menuitem" onClick={() => { logout(); navigate("/login"); }} className="flex w-full cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm text-danger hover:bg-danger-soft">
                    <LogOut size={16} aria-hidden /> Cerrar sesión
                  </button>
                </div>
              )}
            </Dropdown>
          </div>
        </div>
      </header>

      <AnimatePresence>
        {drawer && (
          <motion.div className="fixed inset-0 z-[55] lg:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="absolute inset-0 bg-black/35" onClick={() => setDrawer(false)} aria-hidden />
            <motion.nav
              aria-label="Menú"
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 340, damping: 34 }}
              className="absolute inset-y-0 left-0 w-[82vw] max-w-xs overflow-y-auto bg-surface-solid p-4 shadow-lg"
            >
              <div className="mb-4 flex items-center justify-between">
                <Logo size={30} />
                <button type="button" onClick={() => setDrawer(false)} className="cursor-pointer rounded-md p-2 text-muted hover:bg-surface-muted" aria-label="Cerrar menú">
                  <X size={18} />
                </button>
              </div>
              {areas.map((area) => (
                <div key={area} className="mb-3">
                  <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted">{area}</div>
                  {mods.filter((m) => m.area === area).map((m) => <ModuleLink key={m.key} m={m} />)}
                </div>
              ))}
            </motion.nav>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
