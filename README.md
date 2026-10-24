# 🔧 AutoServicio Demo — gestión de taller con Ingeniería Industrial (+ IA opcional)

> ⚠️ **DEMO CON DATOS FICTICIOS.** "AutoServicio Demo" no es un negocio real. Clientes,
> teléfonos, precios, técnicos y órdenes fueron generados al azar con fines de portafolio.

App web en **Streamlit** para un taller mecánico pequeño (4 técnicos, 3 bahías) que aplica
herramientas de **Ingeniería Industrial** al día a día del taller: estudio de tiempos,
costeo por tiempo estándar, KPIs, Pareto, carga vs. capacidad, secuenciación y control
estadístico. La IA es **opcional**: sin API key la app funciona completa.

## ¿Qué problema resuelve?

En un taller pequeño los precios se calculan "al tanteo", no se sabe cuánto debe tardar
cada trabajo, unos técnicos se saturan mientras otros esperan y los clientes reciben su
auto tarde. Esta app:

- define **tiempos estándar** por servicio y **cotiza con fórmula** (precio consistente y justificable);
- mide **eficiencia** (estándar vs. real) por técnico y **utilización** de bahías;
- detecta los **pocos servicios vitales** (Pareto) y la **sobrecarga** semanal;
- propone el **orden de atención** del backlog (FIFO / SPT / EDD) con Gantt;
- vigila la **variación anormal** de tiempos con una gráfica de control.

## Funciones

### Sin IA (núcleo de la app)
| # | Página | Qué hace |
|---|---|---|
| 1 | Catálogo y tiempos | Catálogo editable de 26 servicios con estudio de tiempos (TN, TS), calculadora con observaciones, refacciones y precios |
| 2 | Cotizador | Horas estándar × tarifa + refacciones, margen configurable, subtotal, IVA 16 %, total. Exporta a **Excel** y convierte en orden |
| 3 | Órdenes | Crear, asignar técnico y bahía, avanzar estado (recibida → en proceso → terminada → entregada), registrar tiempo real vs. estándar |
| 4 | Dashboard | Filtro por fechas; ingresos por mes, ticket promedio, eficiencia por técnico, utilización de bahías, lead time, backlog |
| 5 | Pareto | 80/20 por ingreso y por frecuencia: barras + línea acumulada, clase A |
| 6 | Capacidad | Horas estándar programadas vs. disponibles por técnico y semana, con alerta de sobrecarga |
| 7 | Secuenciación | FIFO, SPT y EDD: tiempo de flujo promedio, retraso promedio, órdenes tarde y diagrama de Gantt (taller completo o por técnico) |
| 8 | Control estadístico | Gráfica X̄ (individuales) con límites ±3σ y regla de racha para un servicio |

### Con IA (opcional, Groq · `llama-3.3-70b-versatile`)
1. **Diagnóstico → cotización**: el cliente describe el problema ("hace ruido al frenar") y la IA
   sugiere servicios **del catálogo** en JSON validado (se descartan códigos inexistentes).
   El precio lo calcula la fórmula, no la IA.
2. **Resumen ejecutivo** del dashboard a partir de los KPIs ya calculados.
3. **Mensaje de WhatsApp** para el cliente con su cotización (importes ya calculados).

Si no hay `GROQ_API_KEY`, estas funciones se ocultan con un aviso. Los errores 401 (key
inválida), 429 (límite de uso) y timeout se muestran con mensajes claros.

## Fórmulas

| Concepto | Fórmula |
|---|---|
| Tiempo normal | TN = tiempo observado promedio × factor de calificación |
| Tiempo estándar | TS = TN × (1 + % suplementos) |
| Mano de obra | Σ horas estándar × cantidad × tarifa por hora |
| Subtotal | (mano de obra + refacciones) × (1 + % margen) |
| IVA / Total | IVA = subtotal × 16 % · Total = subtotal + IVA |
| Ticket promedio | Σ total de órdenes cerradas / número de órdenes cerradas |
| Eficiencia | Σ horas estándar / Σ horas reales (> 100 % = más rápido que el estándar) |
| Utilización de bahía | horas reales usadas / (días laborables × 8 h) |
| Lead time | fecha de entrega − fecha de recepción (promedio, días) |
| Backlog | órdenes en estado recibida o en proceso (y sus horas estándar) |
| Pareto | % acumulado ordenado de mayor a menor; clase A hasta alcanzar 80 % |
| Carga vs. capacidad | Σ horas estándar programadas en la semana vs. 6 días × 8 h por técnico |
| Secuenciación | Flujo Fⱼ = Cⱼ · Retraso Tⱼ = máx(0, Cⱼ − dⱼ) · tarde si Tⱼ > 0 |
| Gráfica de control | LC = x̄ · LSC = x̄ + 3σ · LIC = máx(0, x̄ − 3σ) |

Calendario laboral: lunes a sábado, 9:00–17:00 (8 h). Todas las fórmulas viven en `src/` como
funciones puras con pruebas en `tests/`.

## Instalar y correr en Windows (PowerShell)

Requisitos: Python 3.12 y Git.

```powershell
git clone https://github.com/robertofranco2873/demo-taller-ia.git
cd demo-taller-ia
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1          # si falla: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
python -m src.seed                    # opcional: la app crea la base sola si no existe
streamlit run app.py                  # abre http://localhost:8501
```

Pruebas:

```powershell
python -m pytest -q
```

IA opcional: copia `.env.example` a `.env` y pega tu key gratuita de
[console.groq.com/keys](https://console.groq.com/keys):

```powershell
Copy-Item .env.example .env
notepad .env
```

## Publicar gratis en Streamlit Community Cloud

1. Sube el repositorio a GitHub (público).
2. Entra a [share.streamlit.io](https://share.streamlit.io) con tu cuenta de GitHub → **Create app**.
3. Elige el repo `demo-taller-ia`, rama `main`, archivo principal `app.py`. En *Advanced settings*
   selecciona Python 3.12.
4. (Opcional) En *Secrets* agrega:
   ```toml
   GROQ_API_KEY = "gsk_..."
   ```
5. **Deploy**. La base SQLite se crea sola con datos ficticios al primer arranque. En la nube el
   disco es temporal: los cambios se pierden cuando la app se reinicia (adecuado para un demo).

## Estructura

```
app.py                  Inicio
pages/                  8 páginas de Streamlit (solo UI)
src/                    Lógica pura: time_study, quote, kpis, pareto, capacity,
                        sequencing, spc, workcalendar, orders, db, seed, export, charts
src/ai/                 Cliente Groq (requests) y funciones de IA con JSON validado
tests/                  pytest: fórmulas, base de datos, IA simulada y humo de cada página
data/                   taller.db (no se versiona; se genera sola)
```

## Datos ficticios

`src/seed.py` (semilla fija 42) genera ~6 meses hasta la fecha actual: 26 servicios, 30
refacciones, ~430 órdenes, 4 técnicos con eficiencias distintas (112 %, 100 %, 93 %, 82 %),
estacionalidad mensual y semanal, colas por técnico y bahía, esperas por refacciones
(retrasos), anomalías de tiempo (retrabajos) y un pico de demanda reciente que genera backlog
y sobrecarga.

---
Proyecto de portafolio. **Demo con datos ficticios**; no usar para decisiones reales.
