# CLAUDE.md — demo-taller-ia (V2 web)

App demo de un taller mecánico **ficticio** ("AutoServicio Demo"). V1 en Streamlit: tag `v1-streamlit`.

## Arquitectura
- `src/` — lógica de negocio pura (fórmulas de IE, cotizador, KPIs, Pareto, capacidad,
  secuenciación, SPC, inventario, exportar Excel/PDF, semilla, SQLite en `src/db.py`).
  Sin dependencias web. Toda fórmula nueva lleva prueba en `tests/`.
- `api/` — FastAPI. `api/main.py` arma la app; `api/routers/` un router por área;
  `api/auth.py` bcrypt + JWT y `require_roles(...)`. **Los permisos se validan aquí**,
  nunca solo ocultando botones. En producción sirve `frontend/dist`.
- `frontend/` — React + Vite + TypeScript + Tailwind v4 + Framer Motion + ECharts
  (echarts-for-react) + lucide-react.
  - Design tokens en un solo lugar: `frontend/src/styles/tokens.css` (colores claro/oscuro,
    sombras, radios, espaciado, tipografía). No usar colores sueltos en componentes.
  - Gráficas: tema ECharts en `frontend/src/lib/chartTheme.ts`, un solo eje por gráfica.
  - Permisos del menú en `frontend/src/lib/modules.ts` (deben coincidir con el backend).

## Roles
- `admin`: todo. `recepcion`: cotizador, órdenes, clientes, IA de diagnóstico/WhatsApp.
- `tecnico`: Mi día (cronómetro sobre SUS órdenes), mis indicadores, catálogo de servicios (lectura).

## Reglas
- Todo es DEMO con datos ficticios: mantener el aviso en login, UI, README y exportables.
- La IA (Groq, `src/ai/`) solo interpreta y redacta; nunca calcula precios ni métricas.
  La app funciona completa sin `GROQ_API_KEY`.
- Hardware limitado (Celeron, 8 GB): dependencias ligeras, nada de frameworks pesados.
- Texto con contraste WCAG AA en ambos temas. Responsive (los técnicos usan celular).
- Windows + PowerShell. Python 3.12 en `.venv`; Node portátil en `%LOCALAPPDATA%\Programs\nodejs`.
- Dependencias: `requirements.txt` (producción) y `requirements-dev.txt` (+ pytest, httpx).
- Verificar antes de commit: `python -m pytest -q`, `npm run lint` y `npm run build` en `frontend/`.
- Deploy: `Dockerfile` multietapa + `render.yaml` (Render, plan gratis, un solo servicio).
- `data/taller.db` no se versiona; se regenera con `python -m src.seed` (semilla 42).
- No hacer `git add -A`: `.agents/` y `.claude/` son del usuario.
