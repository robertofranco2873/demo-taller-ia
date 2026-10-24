"""Página de inicio."""
import streamlit as st

from src import config, db, kpis
from src.seed import seed_database
from src.ui_common import ai_enabled, ai_unavailable_notice, demo_banner, money, money_short, setup_page

setup_page(config.BUSINESS_NAME, "🔧")
demo_banner()

st.markdown(
    "App demo para un taller mecánico pequeño (**4 técnicos, 3 bahías**) que aplica herramientas "
    "de **Ingeniería Industrial**: estudio de tiempos, cotización por fórmula, indicadores, "
    "Pareto, carga vs. capacidad, secuenciación y control estadístico de procesos."
)

orders = db.load_orders()
items = db.load_items()
closed = kpis.closed(orders)
bl = kpis.backlog(orders)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Órdenes registradas", f"{len(orders):,}")
c2.metric("Ingresos (cerradas)", money_short(closed["total"].sum()), help=money(closed["total"].sum()))
c3.metric("Ticket promedio", money(kpis.average_ticket(orders)))
c4.metric("Backlog", f"{bl['ordenes']} órdenes", f"{bl['horas_estandar']:.0f} h estándar", delta_color="off")

st.subheader("¿Qué hay en cada página?")
st.markdown("""
| Página | Herramienta de IE | Qué responde |
|---|---|---|
| **Catálogo y tiempos** | Estudio de tiempos (TN, TS) | ¿Cuánto *debe* tardar cada servicio? |
| **Cotizador** | Costeo por tiempo estándar | ¿Cuánto cobrar, con margen e IVA? |
| **Órdenes** | Control de producción | ¿Quién hace qué, en qué bahía y cuánto tardó realmente? |
| **Dashboard** | KPIs de operación | Ingresos, ticket, eficiencia, utilización, lead time, backlog |
| **Pareto** | Análisis 80/20 | ¿Qué pocos servicios generan la mayor parte del negocio? |
| **Capacidad** | Carga vs. capacidad | ¿Quién está sobrecargado esta semana? |
| **Secuenciación** | Reglas FIFO / SPT / EDD + Gantt | ¿En qué orden atender el backlog? |
| **Control estadístico** | Gráfica X̄ ±3σ | ¿Hay variación anormal en los tiempos? |
""")

if ai_enabled():
    st.success("🤖 IA activa (Groq): diagnóstico → cotización, resumen ejecutivo y mensaje de WhatsApp.")
else:
    ai_unavailable_notice()

st.caption("La IA solo interpreta texto y redacta. Todos los precios y métricas se calculan con fórmulas.")

with st.expander("🔄 Regenerar datos de demostración"):
    st.write("Borra la base actual y crea de nuevo ~6 meses de datos ficticios (semilla fija = 42).")
    if st.button("Regenerar base de datos", type="secondary"):
        result = seed_database()
        st.success(f"Listo: {result['orders']} órdenes y {result['items']} servicios generados.")
        st.rerun()
