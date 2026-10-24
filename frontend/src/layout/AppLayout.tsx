import { AnimatePresence, motion } from "framer-motion";
import { Suspense, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { ThemedLoader } from "../components/loaders";
import { useAuth } from "../lib/auth";
import { useHotkey } from "../lib/hooks";
import { HOME_BY_ROLE, moduleByPath } from "../lib/modules";
import type { Role } from "../lib/types";
import { CommandPalette } from "./CommandPalette";
import { TopBar } from "./TopBar";

export function ModuleLoader() {
  const location = useLocation();
  const mod = moduleByPath(location.pathname);
  return <ThemedLoader kind={mod?.loader ?? "gear"} label={mod ? `Cargando ${mod.title.toLowerCase()}…` : "Cargando…"} />;
}

export function AppLayout() {
  const { user, loading } = useAuth();
  const location = useLocation();
  const [palette, setPalette] = useState(false);
  useHotkey("k", () => setPalette((p) => !p));

  if (loading) return <ThemedLoader kind="gear" label="Abriendo el taller…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;

  return (
    <div className="min-h-screen">
      <a href="#contenido" className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-[90] focus:rounded-md focus:bg-surface-solid focus:px-3 focus:py-2">
        Saltar al contenido
      </a>
      <TopBar onSearch={() => setPalette(true)} />
      <main id="contenido" className="mx-auto max-w-7xl px-3 pb-16 pt-5 sm:px-5">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
          >
            <Suspense fallback={<ModuleLoader />}>
              <Outlet />
            </Suspense>
          </motion.div>
        </AnimatePresence>
      </main>
      <footer className="pb-6 text-center text-xs text-muted">
        AutoServicio Demo · proyecto de portafolio · datos ficticios
      </footer>
      <CommandPalette open={palette} onClose={() => setPalette(false)} />
    </div>
  );
}

/** Protege la ruta en el cliente (el backend valida igual cada petición). */
export function RequireRole({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user) return null;
  if (!roles.includes(user.role)) return <Navigate to="/sin-permiso" replace />;
  return <>{children}</>;
}

export function HomeRedirect() {
  const { user } = useAuth();
  return <Navigate to={user ? HOME_BY_ROLE[user.role] : "/login"} replace />;
}
