import streamlit as st

from src import charts, db, kpis
from src.pareto import pareto_table, vital_few
from src.ui_common import date_filter, setup_page

setup_page("Análisis de Pareto (80/20)", "📈")

all_items = db.load_items()
all_orders = db.load_orders()
start, end = date_filter(all_orders, "pareto_dates")
items = kpis.filter_by_date(all_items, start, end)
items = items[items["status"].isin(["terminada", "entregada"])]

mode = st.radio("Criterio", ["Por ingreso", "Por frecuencia"], horizontal=True)
by_value = mode == "Por ingreso"
table = pareto_table(items, "service_name", "line_subtotal" if by_value else None)
if table.empty:
    st.info("No hay servicios cerrados en el periodo.")
    st.stop()

n_a = vital_few(table)
share = table.loc[table["clase"] == "A", "pct"].sum()
st.success(f"**{n_a} de {len(table)} servicios ({n_a / len(table):.0%})** concentran el "
           f"**{share:.0%}** del {'ingreso (sin IVA)' if by_value else 'número de servicios realizados'}.")
st.plotly_chart(charts.pareto(table, "service_name", "Ingreso" if by_value else "Frecuencia"), width="stretch")
st.caption("Barras azul oscuro = clase A (los «pocos vitales» hasta el 80 % acumulado). "
           "Barras y línea comparten el mismo eje en %.")
st.dataframe(table, hide_index=True, width="stretch",
             column_config={"service_name": "Servicio",
                            "valor": st.column_config.NumberColumn("Ingreso" if by_value else "Veces",
                                                                   format="dollar" if by_value else "%d"),
                            "pct": st.column_config.NumberColumn("% del total", format="percent"),
                            "pct_acumulado": st.column_config.NumberColumn("% acumulado", format="percent"),
                            "clase": "Clase"})
