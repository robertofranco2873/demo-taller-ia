import { motion } from "framer-motion";
import { KeyRound, LogIn, Moon, ShieldCheck, Sun, UserRound } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { GearLoader } from "../components/loaders";
import { Logo } from "../components/Logo";
import { Button, Notice } from "../components/ui";
import { useAuth } from "../lib/auth";
import { useApi } from "../lib/hooks";
import { HOME_BY_ROLE } from "../lib/modules";
import { useTheme } from "../lib/theme";
import type { Role } from "../lib/types";

interface DemoUser {
  username: string;
  name: string;
  role: Role;
  role_label: string;
  password: string;
}

const ROLE_INFO: Record<Role, string> = {
  admin: "Todo: dashboard, Pareto, capacidad, secuenciación, catálogo, inventario, usuarios.",
  recepcion: "Cotizador, órdenes, clientes y diagnóstico con IA.",
  tecnico: "Mi día con cronómetro, mis indicadores y fichas de servicio.",
};

export default function Login() {
  const { user, login } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const { data: demo } = useApi<DemoUser[]>("/api/auth/demo-users");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={HOME_BY_ROLE[user.role]} replace />;

  async function submit(e?: FormEvent, u = username, p = password) {
    e?.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const logged = await login(u, p);
      navigate(HOME_BY_ROLE[logged.role]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative grid min-h-screen place-items-center px-4 py-10">
      <button type="button" onClick={toggle} className="absolute right-4 top-4 cursor-pointer rounded-md p-2.5 text-secondary hover:bg-surface-muted" aria-label="Cambiar tema">
        {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
      </button>
      <div className="grid w-full max-w-5xl items-center gap-8 lg:grid-cols-2">
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="hidden lg:block">
          <Logo size={64} />
          <h1 className="mt-6 text-3xl font-bold leading-tight tracking-tight text-text">
            Gestión de taller con <span className="text-accent">Ingeniería Industrial</span>
          </h1>
          <p className="mt-3 max-w-md text-secondary">
            Tiempos estándar, cotizador por fórmula, KPIs, Pareto, capacidad, secuenciación y control estadístico.
            La IA es opcional y nunca calcula precios.
          </p>
          <div className="mt-6 opacity-90"><GearLoader /></div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass rounded-xl bg-surface p-6 sm:p-8">
          <div className="mb-5 lg:hidden"><Logo size={44} /></div>
          <h2 className="text-xl font-bold text-text">Iniciar sesión</h2>
          <Notice kind="warning">
            <strong>Demo con datos ficticios.</strong> “AutoServicio Demo” no es un negocio real. Usa un usuario demo.
          </Notice>
          <form onSubmit={submit} className="mt-5 space-y-4">
            <div>
              <label htmlFor="u" className="field-label">Usuario</label>
              <div className="relative">
                <UserRound size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
                <input id="u" className="field pl-9" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
              </div>
            </div>
            <div>
              <label htmlFor="p" className="field-label">Contraseña</label>
              <div className="relative">
                <KeyRound size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
                <input id="p" type="password" className="field pl-9" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              </div>
            </div>
            {error && <Notice kind="danger">{error}</Notice>}
            <Button type="submit" variant="primary" size="lg" icon={LogIn} loading={busy} className="w-full">Entrar</Button>
          </form>

          <div className="mt-6">
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted">
              <ShieldCheck size={14} aria-hidden /> Usuarios demo (uno por rol)
            </div>
            <div className="grid gap-2">
              {demo?.map((d) => (
                <motion.button
                  key={d.username}
                  type="button"
                  whileHover={{ x: 3 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => {
                    setUsername(d.username);
                    setPassword(d.password);
                    submit(undefined, d.username, d.password);
                  }}
                  className="card-hover cursor-pointer rounded-md border border-border bg-surface-muted p-3 text-left"
                >
                  <div className="flex flex-wrap items-center justify-between gap-1">
                    <span className="text-sm font-semibold text-text">{d.role_label}</span>
                    <code className="rounded bg-surface-solid px-1.5 py-0.5 text-xs text-accent">{d.username} / {d.password}</code>
                  </div>
                  <div className="mt-0.5 text-xs text-muted">{ROLE_INFO[d.role]}</div>
                </motion.button>
              ))}
            </div>
            <p className="mt-3 text-xs text-muted">Contraseñas guardadas con bcrypt; sesión con JWT. Los permisos se validan en el servidor.</p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
