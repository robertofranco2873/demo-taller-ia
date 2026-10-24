import { lazy } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppLayout, HomeRedirect, RequireRole } from "./layout/AppLayout";
import { MODULES } from "./lib/modules";
import type { Role } from "./lib/types";
import Login from "./pages/Login";
import { Forbidden, NotFound } from "./pages/Errors";

// Cada página se descarga solo cuando se visita (más ligero en celular).
const pages: Record<string, React.LazyExoticComponent<() => React.JSX.Element>> = {
  "mi-dia": lazy(() => import("./pages/MiDia")),
  "mis-indicadores": lazy(() => import("./pages/MisIndicadores")),
  servicios: lazy(() => import("./pages/Servicios")),
  cotizador: lazy(() => import("./pages/Cotizador")),
  ordenes: lazy(() => import("./pages/Ordenes")),
  clientes: lazy(() => import("./pages/Clientes")),
  dashboard: lazy(() => import("./pages/Dashboard")),
  pareto: lazy(() => import("./pages/Pareto")),
  capacidad: lazy(() => import("./pages/Capacidad")),
  secuenciacion: lazy(() => import("./pages/Secuenciacion")),
  control: lazy(() => import("./pages/Control")),
  inventario: lazy(() => import("./pages/Inventario")),
  usuarios: lazy(() => import("./pages/Usuarios")),
  configuracion: lazy(() => import("./pages/Configuracion")),
};
const ServicioDetalle = lazy(() => import("./pages/ServicioDetalle"));
const OrdenDetalle = lazy(() => import("./pages/OrdenDetalle"));

const guard = (roles: Role[], el: React.ReactNode) => <RequireRole roles={roles}>{el}</RequireRole>;
const rolesOf = (key: string) => MODULES.find((m) => m.key === key)!.roles;

const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  {
    element: <AppLayout />,
    children: [
      { index: true, element: <HomeRedirect /> },
      ...MODULES.map((m) => {
        const Page = pages[m.key];
        return { path: m.path, element: guard(m.roles, <Page />) };
      }),
      { path: "/servicios/:id", element: guard(rolesOf("servicios"), <ServicioDetalle />) },
      { path: "/ordenes/:id", element: guard(rolesOf("ordenes"), <OrdenDetalle />) },
      { path: "/sin-permiso", element: <Forbidden /> },
      { path: "*", element: <NotFound /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
