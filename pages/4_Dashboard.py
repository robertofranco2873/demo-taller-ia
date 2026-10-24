import streamlit as st

from src import charts, db, kpis
from src.ai.features import executive_summary
from src.ai.groq_client import AIError
from src.ui_common import ai_enabled, ai_unavailable_notice, date_filter, money, money_short, setup_page

setup_page("Dashboard de indicadores", "📊")

all_orders = db.load_orders()
all_items = db.load_items()
start, end = date_filter(all_orders, "dash_dates")
orders = kpis.filter_by_date(all_orders, start, end)
items = kpis.filter_by_date(all_items, start, end)
bays = db.load_bays()["name"].tolist()
st.caption(f"Periodo: {start} a {end} (por fecha de recepción). Ingresos = órdenes terminadas o entregadas, con IVA.")

summary = kpis.summary(orders, items, bays, start, end)
eff = kpis.efficiency_by_technician(items)
util = kpis.bay_utilization(orders, bays, start, end)
c = st.columns(5)
c[0].metric("Ingresos", money_short(summary["ingresos_totales"]), help=money(summary["ingresos_totales"]))
c[1].metric("Ticket promedio", money(summary["ticket_promedio"]))
c[2].metric("Lead time promedio", f"{summary['lead_time_promedio_dias']:.1f} días")
c[3].metric("Eficiencia del taller", f"{eff['std_hours'].sum() / eff['actual_hours'].sum():.0%}" if len(eff) else "—")
c[4].metric("Backlog", f"{summary['backlog_ordenes']} órdenes", f"{summary['backlog_horas_estandar']:.0f} h estándar", delta_color="off")

left, right = st.columns(2)
rev = kpis.revenue_by_month(orders)
left.plotly_chart(charts.revenue_by_month(rev), width="stretch")
right.plotly_chart(charts.efficiency_by_technician(eff), width="stretch")
left, right = st.columns(2)
left.plotly_chart(charts.bay_utilization(util), width="stretch")
with right:
    st.markdown("**Órdenes pendientes (backlog)**")
    pending = orders[orders["status"].isin(["recibida", "en proceso"])]
    st.dataframe(pending[["folio", "status", "technician", "due_date", "std_hours"]].sort_values("due_date"),
                 hide_index=True, width="stretch", height=300,
                 column_config={"folio": "Folio", "status": "Estado", "technician": "Técnico",
                                "due_date": "Compromiso",
                                "std_hours": st.column_config.NumberColumn("Horas est.", format="%.2f")})

with st.expander("📄 Ver tablas de datos"):
    st.dataframe(rev, hide_index=True, width="stretch")
    st.dataframe(eff, hide_index=True, width="stretch")
    st.dataframe(util, hide_index=True, width="stretch")

st.subheader("🤖 Resumen ejecutivo (IA)")
if ai_enabled():
    st.caption("La IA recibe solo los KPIs ya calculados y los explica; no recalcula nada.")
    if st.button("Generar resumen ejecutivo"):
        try:
            with st.spinner("Redactando resumen…"):
                st.session_state.exec_summary = executive_summary(summary)
        except AIError as e:
            st.error(str(e))
    if st.session_state.get("exec_summary"):
        st.markdown(st.session_state.exec_summary)
    with st.expander("KPIs enviados a la IA"):
        st.json(summary)
else:
    ai_unavailable_notice()
