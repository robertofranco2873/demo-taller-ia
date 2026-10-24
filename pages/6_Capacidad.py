from datetime import date, timedelta

import pandas as pd
import streamlit as st

from src import charts, db
from src.capacity import weekly_load
from src.workcalendar import week_start
from src.ui_common import setup_page

setup_page("Carga vs. capacidad semanal", "⚖️")
st.markdown("**Carga** = Σ horas estándar programadas en la semana · **Capacidad** = días laborables × 8 h "
            "(lunes a sábado) · **Utilización** = carga / capacidad")

orders = db.load_orders()
techs = db.load_technicians()["name"].tolist()
this_week = week_start(date.today())
weeks = [this_week + timedelta(weeks=k) for k in range(-8, 4)]
labels = {f"Semana del {w:%d/%m/%Y}" + (" (actual)" if w == this_week else ""): w for w in weeks}
choice = st.select_slider("Semana", list(labels), value=[k for k, v in labels.items() if v == this_week][0])
week = labels[choice]

load = weekly_load(orders, techs, week)
overloaded = load[load["sobrecarga"]]
if len(overloaded):
    st.error("⚠️ Sobrecarga: " + ", ".join(
        f"{r.technician} ({r.utilizacion:.0%}, {-r.holgura_horas:.1f} h de más)" for r in overloaded.itertuples()))
else:
    st.success("✅ Ningún técnico excede su capacidad esta semana.")

st.plotly_chart(charts.load_vs_capacity(load), width="stretch")
st.dataframe(load, hide_index=True, width="stretch",
             column_config={"technician": "Técnico", "ordenes": "Órdenes",
                            "carga_horas": st.column_config.NumberColumn("Carga (h)", format="%.1f"),
                            "capacidad_horas": st.column_config.NumberColumn("Capacidad (h)", format="%.0f"),
                            "utilizacion": st.column_config.NumberColumn("Utilización", format="percent"),
                            "holgura_horas": st.column_config.NumberColumn("Holgura (h)", format="%.1f"),
                            "sobrecarga": st.column_config.CheckboxColumn("⚠ Sobrecarga")})

st.subheader("Utilización por semana (vista general)")
rows = []
for w in weeks:
    wl = weekly_load(orders, techs, w)
    rows.append({"Semana": f"{w:%d/%m}", **{r.technician: r.utilizacion for r in wl.itertuples()}})
overview = pd.DataFrame(rows).set_index("Semana")
st.dataframe(overview.style.format("{:.0%}").map(lambda v: "color: #d03b3b; font-weight: bold" if v > 1 else ""),
             width="stretch")
st.caption("Valores > 100 % en rojo = sobrecarga. Sugerencia: reasignar órdenes en la página Órdenes "
           "o reprogramar a semanas con holgura.")
