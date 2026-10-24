import {
  BarChart3, Boxes, CalendarClock, ClipboardList, Gauge, LineChart, ListOrdered, Settings, Timer, TrendingUp,
  Users, UserSquare2, Wrench, Receipt, type LucideIcon,
} from "lucide-react";
import type { LoaderKind } from "../components/loaders";
import type { Role } from "./types";

/** Módulos de la app. Los roles deben coincidir con los permisos del backend (api/routers/misc.py). */
export interface Module {
  key: string;
  path: string;
  title: string;
  description: string;
  area: "Mi trabajo" | "Operación" | "Análisis" | "Administración";
  roles: Role[];
  icon: LucideIcon;
  loader: LoaderKind;
}

const A: Role = "admin";
const R: Role = "recepcion";
const T: Role = "tecnico";

export const MODULES: Module[] = [
  { key: "mi-dia", path: "/mi-dia", title: "Mi día", description: "Órdenes de hoy y cronómetro", area: "Mi trabajo", roles: [T], icon: Timer, loader: "wrench" },
  { key: "mis-indicadores", path: "/mis-indicadores", title: "Mis indicadores", description: "Eficiencia y tendencia personal", area: "Mi trabajo", roles: [T], icon: TrendingUp, loader: "piston" },
  { key: "servicios", path: "/servicios", title: "Servicios", description: "Catálogo, fichas y estudio de tiempos", area: "Mi trabajo", roles: [A, R, T], icon: Wrench, loader: "gear" },
  { key: "cotizador", path: "/cotizador", title: "Cotizador", description: "Cotización por fórmula, Excel, PDF e IA", area: "Operación", roles: [A, R], icon: Receipt, loader: "gear" },
  { key: "ordenes", path: "/ordenes", title: "Órdenes", description: "Crear, asignar y avanzar órdenes", area: "Operación", roles: [A, R], icon: ClipboardList, loader: "lift" },
  { key: "clientes", path: "/clientes", title: "Clientes", description: "Historial por cliente", area: "Operación", roles: [A, R], icon: UserSquare2, loader: "lift" },
  { key: "dashboard", path: "/dashboard", title: "Dashboard", description: "KPIs con detalle por mes, técnico y KPI", area: "Análisis", roles: [A], icon: Gauge, loader: "piston" },
  { key: "pareto", path: "/pareto", title: "Pareto", description: "80/20 con drill-down", area: "Análisis", roles: [A], icon: BarChart3, loader: "gear" },
  { key: "capacidad", path: "/capacidad", title: "Capacidad", description: "Carga vs. capacidad semanal", area: "Análisis", roles: [A], icon: CalendarClock, loader: "lift" },
  { key: "secuenciacion", path: "/secuenciacion", title: "Secuenciación", description: "FIFO, SPT, EDD, Gantt y reasignar", area: "Análisis", roles: [A], icon: ListOrdered, loader: "wrench" },
  { key: "control", path: "/control", title: "Control estadístico", description: "Gráficas X̄ y X̄-R", area: "Análisis", roles: [A], icon: LineChart, loader: "piston" },
  { key: "inventario", path: "/inventario", title: "Inventario", description: "Stock, punto de reorden y EOQ", area: "Administración", roles: [A], icon: Boxes, loader: "lift" },
  { key: "usuarios", path: "/usuarios", title: "Usuarios", description: "Cuentas y roles", area: "Administración", roles: [A], icon: Users, loader: "gear" },
  { key: "configuracion", path: "/configuracion", title: "Configuración", description: "Parámetros, respaldo y datos demo", area: "Administración", roles: [A], icon: Settings, loader: "wrench" },
];

export const AREAS = ["Mi trabajo", "Operación", "Análisis", "Administración"] as const;

export const ROLE_LABEL: Record<Role, string> = {
  admin: "Administrador / gerente",
  recepcion: "Recepción / asesor",
  tecnico: "Técnico",
};

export const HOME_BY_ROLE: Record<Role, string> = { admin: "/dashboard", recepcion: "/cotizador", tecnico: "/mi-dia" };

export function modulesFor(role: Role | undefined) {
  return role ? MODULES.filter((m) => m.roles.includes(role)) : [];
}

export function moduleByPath(pathname: string) {
  return MODULES.find((m) => pathname === m.path || pathname.startsWith(`${m.path}/`));
}
