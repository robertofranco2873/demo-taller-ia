# Reporte de estado: AutoServicio Demo como DEMO 1 del portafolio

Fecha de revisión: 24 oct 2026 · Rama `main` en el commit `b95619f`. Secciones 7 y 8 actualizadas en la rama `feature/demo-publica`.

En este paso no se cambió código: solo se revisó, ejecutó y midió. Todo lo de las secciones 3 a 6 se
corrió de verdad; donde algo no se pudo verificar, se dice.

**Veredicto corto:** como app local la demo está **lista**. Las pruebas, la compilación y el
recorrido por roles salieron limpios, y la instalación desde cero funciona siguiendo el README.
**No está lista como demo en línea**: no hay deploy, la descripción del repo está desactualizada y
falta proteger la demo pública contra visitantes que borren o cambien los datos (ver sección 8).

---

## 1. Resumen de cambios desde `v1-streamlit`

`git log v1-streamlit..HEAD` muestra **10 commits** (6 de fases, 1 merge y 3 mejoras posteriores):

```
b95619f Secuenciación: mover órdenes a otro técnico desde la tabla (...)
cfd98f0 Secuenciación: prioridad manual editable (...), Gantt por días laborables (...)
8ab0992 Inicio con doble clic: Iniciar AutoServicio.bat (...) e ícono del logo
01b598d Merge feature/v2-web: V2 web (FastAPI + React) (...)
eb44c11 Fase 5: deploy en Render (Dockerfile + render.yaml), README V2 (...)
9f13f60 Fase 4: páginas V2 (...)
5d747cb Fase 3: frontend React+Vite+TS+Tailwind (...)
8c2efa9 Fase 2: API REST con FastAPI (...); se retira la UI Streamlit
1d0939d Fase 1: lógica V2 (X̄-R, observaciones necesarias, (...))
052a1a8 Fase 0: pendientes de V2 y CLAUDE.md
```

`git diff --stat v1-streamlit..HEAD`: **123 archivos, +12,465 / −1,115 líneas**. Sin contar
`package-lock.json` ni imágenes: **108 archivos, +8,343 / −1,115**. Hay 94 archivos nuevos, 15
modificados y 14 eliminados (toda la UI Streamlit: `app.py`, `paginas/`, `src/ui_common.py`,
`src/charts.py`, `tests/test_pages.py`, `.streamlit/`).

Qué cambió, por área:

| Área | Antes (V1) | Ahora (V2) |
|---|---|---|
| **Diseño** | Tema por defecto de Streamlit | Identidad propia: design tokens en un solo archivo, paleta dorado/azul/morado con contraste AA verificado, vidrio esmerilado, modo claro y oscuro, logo SVG y favicon, 4 animaciones de carga temáticas, skeletons, tooltips, confeti, transiciones y diseño responsive |
| **Roles** | Sin login; cualquiera veía todo | Login con bcrypt + JWT y tres roles (admin, recepción, técnico) validados en **cada endpoint** del backend |
| **Dashboard** | KPIs y gráficas estáticas | KPIs con conteo animado e inclinación 3D; ventanas emergentes por KPI (fórmula, cálculo, tendencia), por mes (órdenes, ingresos por servicio, comparativo y técnicos destacados) y por técnico |
| **Pareto** | Gráfica de un solo nivel | Drill-down de 3 niveles con breadcrumbs: servicios → servicio (histórico, técnicos, real vs. estándar, gráfica de control) → órdenes → detalle de cada orden; tabla accesible con teclado |
| **Técnicos** | No existía vista propia | **Mi día** con cronómetro (iniciar, pausar, terminar), ficha de cada servicio, aviso de tiempo sospechoso y confeti; **Mis indicadores** |
| **Navegación** | Menú lateral de Streamlit | Barra superior con menús por área, búsqueda, notificaciones por rol, cambio de tema, menú de usuario, paleta **Ctrl+K**, breadcrumbs y cajón lateral en celular |
| **IA** | 3 funciones con Groq | Las mismas 3 (diagnóstico → cotización, resumen ejecutivo, WhatsApp), ahora como endpoints protegidos por rol; modelo `qwen/qwen3.8-27b`; manejo de 401, 404, 429 y timeout |
| **Backend** | Streamlit llamando a `src/` | API REST FastAPI (60 rutas) que reutiliza `src/`. Funciones nuevas: X̄-R, observaciones necesarias, programación con bahías, prioridad manual y mover órdenes entre técnicos, inventario (ROP, EOQ), cotización en PDF, usuarios, respaldo y restauración, cronómetro, migración automática de la base |
| **Operación** | `streamlit run` | `Iniciar AutoServicio.bat` con doble clic; Dockerfile y `render.yaml` para Render |

## 2. Arquitectura actual

**Stack:**
- Backend: Python 3.12, FastAPI, uvicorn, SQLite, pandas, bcrypt, PyJWT, fpdf2, openpyxl y requests (para Groq).
- Frontend: React 19, Vite 6, TypeScript 5.8, Tailwind v4, Framer Motion, Apache ECharts 5 (modular), lucide-react y canvas-confetti.
- Pruebas: pytest y httpx.

```
api/        main.py (app, sirve el frontend compilado), core.py (JWT, require_roles), routers/ (9 por área)
src/        lógica pura: time_study, quote, kpis, analytics, pareto, capacity, sequencing, spc, inventory,
            orders, workcalendar, export (Excel/PDF), security (bcrypt), db (SQLite + migración), seed, ai/
frontend/   src/styles/tokens.css (design tokens), lib/ (cliente API, auth, tema, gráficas), components/,
            layout/ (barra superior, Ctrl+K), pages/ (18 páginas con carga diferida)
tests/      14 archivos · 226 pruebas
docs/       pendientes-v2.md, capturas/ (12 PNG), este reporte
Dockerfile · render.yaml · Iniciar AutoServicio.bat · iniciar.ps1
```

**Cómo se conecta el frontend con el backend:**
- **Peticiones:** el frontend hace `fetch` a `/api/...` con `Authorization: Bearer <JWT>`; el token vive en `localStorage`. Un 401 cierra la sesión.
- **Producción:** FastAPI sirve `frontend/dist` en el mismo origen, con *fallback* de SPA. Es un solo servicio y un solo puerto.
- **Desarrollo:** Vite corre en el puerto 5173 y redirige `/api` a uvicorn en el 8000.
- **Permisos:** el backend consulta al usuario en la base en cada petición y aplica `require_roles(...)`. El frontend también oculta menús y rutas (`RequireRole`), pero eso es solo comodidad.
- **Base de datos:** SQLite en `data/taller.db` (configurable con `TALLER_DB_PATH`). Si no existe, se crea con datos ficticios; si es de una versión anterior, se migra.

## 3. Funciones por rol

Leyenda: ✅ funciona (verificado en esta revisión) · 🟡 parcial o verificado solo en parte · ❌ no funciona o no existe.

### Administrador / gerente (`gerente`)
| Función | Estado | Cómo se verificó |
|---|---|---|
| Dashboard: 6 KPIs, ventanas por KPI, mes y técnico, filtro de fechas | ✅ | Navegador: los 3 modales se abrieron; pytest |
| Pareto con drill-down de 3 niveles y detalle de orden | ✅ | Navegador: nivel 2, nivel 3, detalle y regreso por breadcrumb |
| Capacidad semanal y vista de 12 semanas | ✅ | La página carga sin errores; pytest |
| Secuenciación: FIFO/SPT/EDD, prioridad manual, mover órdenes entre técnicos, Gantt por días, guardar | ✅ | Navegador: se movió OT-00421 a Lucía, se guardó y apareció en su Mi día |
| Control estadístico X̄ y X̄-R, filtro por técnico | ✅ | La página carga; pytest de los endpoints |
| Catálogo y estudio de tiempos (editar, calculadora de observaciones) | ✅ | La página carga; pytest del PUT y del cálculo |
| Cotizador, órdenes y clientes (todo lo de recepción) | ✅ | Ver recepción |
| Inventario (ROP, EOQ, movimientos) | 🟡 | La página carga y la API está probada; el modal de movimientos no se usó en el navegador |
| Usuarios (crear, editar, desactivar, borrar) | 🟡 | API probada con pytest; en el navegador solo se verificó que la página carga |
| Configuración: parámetros, respaldo y restauración, regenerar datos | 🟡 | API probada con pytest (incluye restauración inválida y válida); en el navegador solo carga |
| Resumen ejecutivo con IA | 🟡 | Sin key: aviso correcto y 503 controlado. Con key: no se probó en la V2 |

### Recepción / asesor (`recepcion`)
| Función | Estado | Cómo se verificó |
|---|---|---|
| Cotizador por fórmula (total en vivo) | ✅ | API sin IA: total $2,868.39, igual que en la V1 |
| Exportar a PDF y Excel | ✅ | Descarga de PDF en el navegador; API: PDF `%PDF` y Excel `PK` |
| Convertir cotización en orden | ✅ | pytest (crear orden y avanzar hasta "terminada") |
| Órdenes: lista, filtros, detalle, asignación, avance de estado | ✅ | Páginas sin errores; pytest del ciclo completo |
| Clientes e historial | ✅ | La página carga; pytest |
| Catálogo de servicios (lectura) | ✅ | La página carga |
| Diagnóstico con IA y mensaje de WhatsApp | 🟡 | Sin key se ocultan con aviso (verificado). Con key solo hay pruebas simuladas; no se probó con Groq real en la V2 |
| Bloqueo de módulos de admin | ✅ | `/dashboard` redirige a `/sin-permiso`; la API devuelve 403 |

### Técnico (`tecnico`, `lucia`, `miguel`, `sofia`)
| Función | Estado | Cómo se verificó |
|---|---|---|
| Mi día: órdenes por prioridad (o por la secuencia guardada) | ✅ | Navegador y pytest |
| Cronómetro iniciar → pausar → terminar, confeti, aviso si el tiempo es muy bajo | ✅ | Navegador |
| Ficha rápida del servicio (pasos, estándar, refacciones) | ✅ | La API de ficha responde 200 al técnico |
| Mis indicadores (eficiencia vs. meta, semanal, servicios) | ✅ | La página carga sin errores |
| Catálogo de servicios (lectura) | ✅ | La página carga |
| Vista en celular y modo oscuro | ✅ | Captura móvil de 390 px en modo oscuro |
| Solo ve **sus** órdenes | ✅ | 403 en órdenes ajenas y al iniciar el cronómetro en una orden ajena; la búsqueda solo muestra las propias |
| Bloqueo de admin y recepción | ✅ | 403 en los 29 endpoints de admin y en los de recepción |

### Transversal
| Función | Estado |
|---|---|
| Login con usuarios demo visibles; contraseña incorrecta → 401 | ✅ |
| Ctrl+K (módulos, servicios, órdenes, técnicos según el rol) | ✅ |
| Notificaciones por rol | ✅ |
| Todo funciona sin `GROQ_API_KEY` | ✅ |
| Doble clic en `Iniciar AutoServicio.bat` | ✅ (en un clon limpio) |
| Deploy en Render | ❌ (no existe; la imagen Docker nunca se construyó) |

## 4. Verificación ejecutada (resultados reales)

### pytest
```
225 passed, 1 skipped, 1 warning in 19.60s
```
- **Prueba omitida:** `POST /api/admin/reseed` dentro de la matriz de permisos se omite a propósito (borraría los datos del módulo); se prueba aparte en `test_reseed_admin`.
- **Advertencia:** `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`
- **Pruebas por archivo:** test_api 126 · test_v2_logic 30 · test_ai 13 · test_kpis 9 · test_time_study 9 · test_workcalendar 8 · test_quote 7 · test_sequencing 7 · test_db_seed 5 · test_orders 4 · test_pareto_capacity 4 · test_spc 4.

### Frontend
```
tsc -b --noEmit          → exit 0, sin errores
npm run lint             → eslint . --max-warnings 0 → exit 0, 0 errores, 0 avisos
npm run build            → ✓ built in 38.40s
  echarts 608.72 kB (gzip 203.64) · index 270.87 kB (gzip 83.32) · motion 148.23 kB (gzip 49.38) · react 97.71 kB (gzip 32.91)
  páginas con carga diferida: de 2 a 15 kB cada una
```

### Arranque de la app, página por página
Servidor `uvicorn` sobre una **copia** de la base (tus datos no se tocaron) y con `GROQ_API_KEY`
vacía. Navegador Edge en modo headless con Playwright; se registraron errores de consola, `pageerror` y
respuestas HTTP ≥ 500:
```
[OK] gerente   /dashboard /pareto /capacidad /secuenciacion /control /servicios /servicios/1
               /cotizador /ordenes /ordenes/5 /clientes /inventario /usuarios /configuracion
[OK] recepcion /cotizador /ordenes /clientes /servicios
[OK] recepcion /dashboard        -> /sin-permiso
[OK] tecnico   /mi-dia /mis-indicadores /servicios /servicios/3
[OK] tecnico   /dashboard        -> /sin-permiso
[OK] tecnico   /ordenes          -> /sin-permiso
PROBLEMAS: 0
```
Interacciones:
```
KPI modal OK · Mes modal OK · Técnico modal OK · Paleta OK: 2 resultados
Pareto nivel 2 OK · Pareto nivel 3 + orden OK · Breadcrumb regreso OK
PDF descargado: cotizacion_2026-10-24.pdf
Aviso de tiempo sospechoso mostrado OK · Cronómetro iniciar/pausar/terminar OK
Mover orden: OT-00421 Carlos → Lucía; en Mi día de Lucía: True; ya no está en Mi día de Carlos: True
ERRORES: ninguno
```
Log del servidor: 0 tracebacks, 0 respuestas 500.

### Login con cada usuario demo
```
gerente    -> HTTP 200  rol=admin
recepcion  -> HTTP 200  rol=recepcion
tecnico    -> HTTP 200  rol=tecnico
lucia      -> HTTP 200  rol=tecnico
miguel     -> HTTP 200  rol=tecnico
sofia      -> HTTP 200  rol=tecnico
contraseña incorrecta -> HTTP 401
visibles en el login: gerente, recepcion, tecnico
```

### Permisos (las 60 rutas del OpenAPI con los tokens de técnico, recepción y gerente)
- **Bloqueo al técnico:** recibe **403 en los 29 endpoints exclusivos de admin**: dashboard, Pareto, capacidad, secuenciación, SPC, inventario, usuarios, configuración, respaldo, restauración y regeneración. También en los de recepción: cotizador, órdenes, clientes, técnicos, bahías, refacciones e IA.
- **Lo que el técnico sí puede usar:** `GET /api/me/day`, `GET /api/me/indicators`, `POST /api/me/orders/{id}/start|pause|finish` (solo sobre sus órdenes), `GET /api/orders/{id}` (solo las suyas), `GET /api/services`, `GET /api/services/{id}`, `POST /api/time-study` (solo calcula), `GET /api/search`, `GET /api/notifications`, `GET /api/ai/status` y `GET /api/health`.
- **Sin sesión:** sin token → 401; token falso → 401.
- **Órdenes ajenas:** el técnico recibe 403 en órdenes de otros técnicos (OT 428, 427 y 426) y al iniciar su cronómetro; la búsqueda le devuelve solo sus propias órdenes.
- **Errores de servidor:** el único 5xx fue `POST /api/ai/summary` → **503 sin key, que es intencional** (mensaje: "Las funciones de IA están desactivadas: falta GROQ_API_KEY").

### Sin `GROQ_API_KEY`
```
ai/status: {'enabled': False, 'model': None}
ai/diagnosis -> 503 "Las funciones de IA están desactivadas: falta GROQ_API_KEY."
cotización por fórmula sin IA -> total 2868.39 · PDF: 200 b'%PDF' · Excel: 200 b'PK'
UI: /cotizador muestra "Funciones de IA desactivadas" y oculta "Sugerir servicios";
    /dashboard y /configuracion muestran "IA desactivada".
```

## 5. Instalación desde cero

Se clonó `https://github.com/robertofranco2873/demo-taller-ia.git` en `%TEMP%\demo-taller-clon` y se
siguió el README ("Desde PowerShell") paso a paso. Al final se probó también el doble clic:

| Paso | Resultado | Tiempo |
|---|---|---|
| `git clone` (commit `b95619f`) | ✅ | 3 s |
| `py -3.12 -m venv .venv` | ✅ | 30 s |
| `pip install -r requirements-dev.txt` | ✅ (43 paquetes, 200 MB) | 3 min 29 s |
| `cd frontend; npm install` | ✅ (202 paquetes) | **6 min 31 s** |
| `npm run build` | ✅ | 1 min 10 s |
| `npm run lint` | ✅ | 19 s |
| `python -m pytest -q` | ✅ 225 passed, 1 skipped | 34 s |
| `uvicorn api.main:app` → `/api/health` y `/login` | ✅; crea la base sola | 9 s |
| `Iniciar AutoServicio.bat` (puerto 8032) | ✅ arranca la app | 19 s |

Observaciones:
- **No falló ningún paso.** El primer arranque completo tarda unos **12 minutos en el Celeron**, sobre todo por `npm install`.
- **Node.js:** el README lo pide como requisito, pero no explica cómo instalarlo. En esta PC está en versión portátil en `%LOCALAPPDATA%\Programs\nodejs`; en una PC nueva habría que instalarlo desde nodejs.org.
- **Activación del entorno:** no se usó `.\.venv\Scripts\Activate.ps1`; los comandos llamaron directo a `.venv\Scripts\python.exe`. La activación depende de la política de ejecución, y el README ya lo advierte.
- **Sin probar:** el Dockerfile y Render (no hay Docker en esta PC). El modo de producción que usa el contenedor (FastAPI sirviendo `dist`) sí está verificado.

## 6. Seguridad

| Revisión | Resultado |
|---|---|
| ¿`.env` alguna vez en el historial? (`git log --all -- .env`) | No: 0 commits |
| Archivos sensibles en el historial (`.env`, `.db`, `.pem`, `.key`, secrets, credentials) | Ninguno |
| Patrones de secretos en todo el historial (`git log -p --all`): `gsk_`, `sk-`, `ghp_`, `gho_`, `AKIA`, JWT `eyJ…`, llaves privadas | 0 coincidencias en todos |
| `.env.example` | `GROQ_API_KEY=` y `JWT_SECRET=` vacíos |
| Contraseñas en el código | Solo la demo pública `DEMO_PASSWORD = "demo123"` (intencional y documentada) |
| Hashes de contraseñas versionados | Ninguno (la base no se versiona) |
| `.gitignore` | Incluye `.env`, `.venv`, `data/*.db`, `node_modules`, `dist` y `*.lnk` |
| Correo personal | No aparece en archivos, pero sí como **autor de los 19 commits** (`roberto.franco2873@gmail.com`), lo cual es público en GitHub |

La key real de Groq vive solo en `.env`, que git ignora. Nunca se subió.

## 7. Checklist de portafolio

*Actualizado el 24 oct 2026 tras la rama `feature/demo-publica`.*

| Punto | ¿Listo? | Comentario |
|---|---|---|
| README claro con aviso de datos ficticios | **Sí** | Aviso al inicio y al final; sección «Ver la demo en línea», modo demo, secuenciación nueva (prioridades, mover órdenes, Gantt por días), regla de eficiencia, variables de entorno, enlaces a Python, Node.js y Git, y pasos de Render |
| Usuarios demo visibles | **Sí** | Botón por rol en el login y tabla en el README; en la demo pública no se pueden borrar ni cambiar su contraseña o rol |
| Repo público listo | **Sí** | Descripción actualizada (ya no dice Streamlit), 13 topics (fastapi, react, typescript, industrial-engineering, ai, groq, portfolio, …), rama vieja `feature/v2-web` borrada, commits nuevos con correo privado `…@users.noreply.github.com` |
| Deploy en línea (URL) | **Sí** · https://demo-taller-ia.onrender.com (Render, plan free, Live) | Blueprint listo (`render.yaml`, plan gratuito, `DEMO_MODE=true`, `APP_TZ`, `JWT_SECRET` generado, `GROQ_API_KEY` secreta). Arranque de producción simulado sin Docker: ✅. Falta crear el servicio en Render y poner la URL real en el README |
| Capturas de pantalla o GIF | **Sí** | 12 capturas (Secuenciación renovada, sin barra superpuesta) + `docs/capturas/recorrido.gif` (10 cuadros, 606 KB, 3 roles) |
| Guion de video | **Sí** | `docs/guion-video.md` (90 s, tres roles, con tiempos y voz) |

## 8. Bugs y riesgos conocidos (de mayor a menor gravedad)

**Resueltos en `feature/demo-publica`:**

| # original | Riesgo | Cómo se resolvió | Verificación |
|---|---|---|---|
| 2 | Demo pública sin protección | `DEMO_MODE=true`: 403 amable al restaurar, regenerar, borrar o desactivar usuarios, cambiar contraseñas y cambiar el rol de los usuarios demo; la base se restablece al arrancar y cada 24 h (regeneración atómica). En la UI, controles deshabilitados con el globo «Desactivado en la demo pública» | `tests/test_demo_mode.py` (con y sin modo demo, reinicio al arrancar y periódico); recorrido headless con `DEMO_MODE=true` |
| 3 | Zona horaria del servidor (UTC) | `src/clock.py` con `zoneinfo` + `tzdata`; `APP_TZ` (por defecto `America/Mexico_City`) en todo «hoy»/«ahora» del backend | `tests/test_clock.py`: cambio de día a las 18:00 CDMX = 00:00 UTC |
| 4 | Datos que envejecen («todo en rojo») | Semilla relativa a hoy: promesas según la cola, una orden en curso por técnico, 2-4 vencidas y algunas listas para entregar | `tests/test_seed_fresh.py` con 7 fechas simuladas; en el arranque simulado: 434 órdenes, 4 en proceso, 2 vencidas (12 %) |
| 5 | Docker/Render sin probar, imágenes sin fijar | `node:24.21.0-bookworm-slim` y `python:3.12.14-slim-bookworm` (etiquetas verificadas en Docker Hub), usuario sin privilegios. Sin Docker local: se simularon las dos etapas (npm ci + build limpio; solo `requirements.txt`, `api/`, `src/`, `dist`, sin `.env`) y se arrancó con el mismo comando del `CMD`, `PORT=10000` y `DEMO_MODE=true` | Arranque OK en 29 s; HTML, `/docs`, rutas SPA, 403 del modo demo y 0 tracebacks |
| 6 | Documentación pública desactualizada | Descripción, topics, README, captura y GIF (ver sección 7) | Revisado con `gh repo view` |
| 7 | IA con key real no verificada en la V2 | Probadas de verdad las 3 funciones (API y UI). Se corrigió que el resumen **calculaba** cifras (p. ej. «94.6 %»): ahora el backend envía los KPIs ya calculados y formateados (incl. tasa de cierre) y el prompt prohíbe calcular y redondear | 4 diagnósticos (solo códigos del catálogo), WhatsApp con importes exactos, 3 resúmenes con 0 cifras ajenas a los KPIs |
| 9 | Eficiencias extremas (3300 %) | Se excluyen registros con tiempo real < 25 % del estándar y la eficiencia se limita a 0-200 %; regla en el globo del KPI; el aviso de Mi día dice cuando no cuenta | `tests/test_efficiency_rule.py` |
| 13 | Correo personal en commits | Commits nuevos con `330761939+robertofranco2873@users.noreply.github.com` (config local del repo). El historial anterior no se reescribió | `git log` de la rama |
| — | Eje del Gantt desfasado (hallado en esta rama) | Marcas en horas exactas de cada día aunque hoy empiece a media jornada | Captura de Secuenciación |

**Pendientes / riesgos que siguen:**

1. **Alta: falta el deploy real.** Todo está listo, pero el servicio en Render lo tienes que crear tú (pasos en el README). Hasta entonces no hay URL.
2. **Media: cuota de Groq en una demo pública.** Con la IA activa, muchas visitas seguidas agotan el límite gratuito (se reprodujo: 4 resúmenes seguidos → 429). La app responde con un mensaje claro («Espera un minuto y reintenta») y todo lo demás sigue funcionando; si molesta, se puede limitar por IP o dejar la demo sin key.
3. **Media: imagen Docker no construida localmente.** La simulación cubre contenido, dependencias y arranque, pero no el build real en Linux; el primer deploy en Render es la prueba definitiva.
4. **Baja: arranque en frío.** Con `DEMO_MODE=true` el arranque regenera la base (≈29 s en el Celeron; menos en Render). Sumado al «despertar» del plan gratis, la primera visita tarda alrededor de un minuto (documentado en el README).
5. **Baja: aviso de npm.** npm 11 no ejecuta el script `postinstall` de esbuild (`npm warn install-scripts`); no afecta porque el binario llega por su paquete de plataforma (build verificado), pero conviene vigilarlo.
6. **Baja: frontend usa la hora del navegador** para valores por defecto de formularios (fechas de una orden nueva); el servidor ya usa `APP_TZ`.
7. **Baja:** `StarletteDeprecationWarning` (httpx en TestClient); ECharts pesa 609 kB (204 kB gzip); `JWT_SECRET` aleatorio en local si no se define; restauración sobre la base en uso (bloqueada en la demo pública).
8. **Higiene local** (no afecta al repo): el `.venv` conserva restos de Streamlit (`~treamlit`); `.agents/` y `.claude/` sin versionar; el correo global de git sigue siendo el personal (la config del repo usa el privado).

## 9. Métricas

**Líneas de código** (sin líneas vacías, solo archivos versionados):

| Parte | Líneas | Archivos |
|---|---:|---:|
| Lógica pura `src/` | 1,856 | 20 |
| IA `src/ai/` | 124 | 3 |
| API FastAPI `api/` | 1,011 | 13 |
| Pruebas `tests/` | 926 | 14 |
| Frontend: páginas | 2,181 | 18 |
| Frontend: componentes | 841 | 9 |
| Frontend: layout | 424 | 3 |
| Frontend: lib (API, tema, gráficas) | 697 | 10 |
| Frontend: estilos y tokens | 389 | 2 |
| Documentación `.md` | 200 | 3 |
| **Total Python (sin pruebas)** | **2,867** | |
| **Total frontend (TS/TSX/CSS)** | **4,602** | |

**Endpoints:** 60 rutas en el OpenAPI (`/docs`). 29 son exclusivas de admin, 13 están disponibles para el técnico y 3 son públicas (`/api/health`, `/api/auth/login`, `/api/auth/demo-users`).

**Pruebas:** 226 en total: 225 pasan y 1 se omite a propósito; 126 son de API y permisos. Corren en unos 20 s.

**Dependencias:**

| | Directas | Instaladas | Tamaño |
|---|---|---|---|
| Python | 10 de ejecución + 2 de desarrollo | 43 paquetes (clon limpio) | ~200 MB en `.venv` |
| npm | 8 de ejecución + 14 de desarrollo | 202 paquetes | 195 MB en `node_modules` |
| Lo que se publica (`frontend/dist`) | | | **1.3 MB** (~370 kB gzip de JS si se visitan todas las páginas) |

El `.venv` de esta PC pesa 449 MB porque arrastra paquetes de la V1.
