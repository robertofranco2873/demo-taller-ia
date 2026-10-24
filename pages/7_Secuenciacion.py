from datetime import datetime

import streamlit as st

from src import charts, db
from src.config import PENDING_STATUSES
from src.sequencing import RULES, Job, compare_rules, schedule
from src.workcalendar import add_work_hours, work_hours_until
from src.ui_common import setup_page

setup_page("Secuenciación de órdenes pendientes", "🗓️")
st.markdown("**Flujo** F = fin de la orden · **Retraso** T = máx(0, fin − fecha compromiso) · "
            "Tiempos en horas laborables desde ahora; tiempo de proceso = horas estándar.")
with st.expander("Reglas"):
    for k, v in RULES.items():
        st.markdown(f"- **{k}**: {v}")

orders = db.load_orders()
pending = orders[orders["status"].isin(PENDING_STATUSES)]
if pending.empty:
    st.info("No hay órdenes pendientes.")
    st.stop()

techs = db.load_technicians()["name"].tolist()
scope = st.radio("Alcance", ["Taller completo (4 técnicos en paralelo)", "Por técnico"], horizontal=True)
now = add_work_hours(datetime.now().replace(microsecond=0), 0)
if scope == "Por técnico":
    tech = st.selectbox("Técnico", techs)
    pending = pending[pending["technician"] == tech]
    machines, names = 1, [tech]
else:
    machines, names = len(techs), techs

jobs = [Job(r.folio, float(r.std_hours), work_hours_until(now, r.due_date), r.created_at.timestamp())
        for r in pending.itertuples()]
if not jobs:
    st.info("Este técnico no tiene órdenes pendientes.")
    st.stop()
st.caption(f"{len(jobs)} órdenes · {sum(j.processing for j in jobs):.1f} h estándar · "
           f"inicio del programa: {now:%a %d/%m %H:%M}")

table = compare_rules(jobs, machines, names)
best_flow = table.loc[table["flujo_promedio_h"].idxmin(), "regla"]
best_tard = table.loc[table["retraso_promedio_h"].idxmin(), "regla"]
st.subheader("Comparativa de reglas")
shown = table.rename(columns={"regla": "Regla", "flujo_promedio_h": "Flujo promedio",
                              "retraso_promedio_h": "Retraso promedio", "ordenes_tarde": "Órdenes tarde",
                              "makespan_h": "Makespan"})
st.dataframe(shown.style.highlight_min(subset=["Flujo promedio", "Retraso promedio", "Órdenes tarde"],
                                       props="font-weight: bold; background-color: rgba(42,120,214,0.15)")
             .format({"Flujo promedio": "{:.1f} h", "Retraso promedio": "{:.1f} h", "Makespan": "{:.1f} h"}),
             hide_index=True, width="stretch")
st.caption(f"Menor flujo promedio: **{best_flow}** · Menor retraso promedio: **{best_tard}**. "
           "Las órdenes ya vencidas cuentan como tarde con cualquier regla.")

rule = st.radio("Regla para el diagrama de Gantt", list(RULES), horizontal=True, index=list(RULES).index(best_tard))
sched = schedule(jobs, rule, machines, names)
st.plotly_chart(charts.gantt(sched, now, f"Gantt — regla {rule}"), width="stretch")
st.dataframe(sched, hide_index=True, width="stretch",
             column_config={"posicion": "#", "orden": "Folio", "recurso": "Técnico",
                            "proceso_h": st.column_config.NumberColumn("Proceso (h)", format="%.2f"),
                            "entrega_h": st.column_config.NumberColumn("Vence en (h)", format="%.1f"),
                            "inicio_h": st.column_config.NumberColumn("Inicio (h)", format="%.1f"),
                            "fin_h": st.column_config.NumberColumn("Fin (h)", format="%.1f"),
                            "flujo_h": st.column_config.NumberColumn("Flujo (h)", format="%.1f"),
                            "retraso_h": st.column_config.NumberColumn("Retraso (h)", format="%.1f"),
                            "tarde": st.column_config.CheckboxColumn("Tarde")})
if scope != "Por técnico":
    st.caption("En «taller completo» cada orden se asigna al técnico que se libera primero; "
               "puede diferir de la asignación actual registrada en la orden.")
