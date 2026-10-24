import streamlit as st

from src import charts, db
from src.spc import control_chart
from src.ui_common import setup_page

setup_page("Gráfica de control de tiempos reales", "🎯")
st.markdown("**LC** = media de los tiempos reales · **LSC / LIC** = media ± 3σ (σ = desviación estándar muestral; "
            "LIC no baja de 0). Señales: punto fuera de límites o racha de 7 puntos del mismo lado de la media.")

items = db.load_items().dropna(subset=["actual_hours"]).sort_values("created_at")
items["valor"] = items["actual_hours"] / items["qty"]  # horas por unidad de servicio
counts = items.groupby("service_name").size()
eligible = counts[counts >= 10].sort_values(ascending=False)
if eligible.empty:
    st.info("Se necesitan al menos 10 registros de tiempo real de un servicio.")
    st.stop()

c1, c2 = st.columns([3, 1])
service = c1.selectbox("Servicio", eligible.index.tolist(),
                       format_func=lambda s: f"{s} ({eligible[s]} registros)")
last_n = c2.number_input("Últimos N registros", 10, int(eligible[service]), min(50, int(eligible[service])))

data = items[items["service_name"] == service].tail(int(last_n)).reset_index(drop=True)
df, limits = control_chart(data["valor"].tolist())
df["folio"] = data["folio"]
df["technician"] = data["technician"]
df["fecha"] = data["created_at"].dt.date

std = float(data["std_hours"].iloc[-1] / data["qty"].iloc[-1])
m = st.columns(5)
m[0].metric("Media (LC)", f"{limits['lc']:.2f} h")
m[1].metric("σ", f"{limits['sigma']:.2f} h")
m[2].metric("LSC", f"{limits['lsc']:.2f} h")
m[3].metric("LIC", f"{limits['lic']:.2f} h")
m[4].metric("Tiempo estándar", f"{std:.2f} h", f"{limits['lc'] / std - 1:+.0%} media vs. estándar", delta_color="inverse")

st.plotly_chart(charts.control_chart(df, limits, f"Gráfica X̄ (individuales) — {service}"), width="stretch")

signals = df[df["fuera_de_limites"] | df["racha"]]
if signals.empty:
    st.success("✅ Proceso bajo control estadístico: no hay señales de variación anormal.")
else:
    st.error(f"⚠️ {len(signals)} punto(s) con señal de variación anormal. Investiga causa asignable "
             "(retrabajo, refacción incorrecta, técnico nuevo, herramienta).")
    st.dataframe(signals[["n", "fecha", "folio", "technician", "valor", "fuera_de_limites", "racha"]],
                 hide_index=True, width="stretch",
                 column_config={"n": "Muestra", "fecha": "Fecha", "folio": "Folio", "technician": "Técnico",
                                "valor": st.column_config.NumberColumn("Horas reales", format="%.2f"),
                                "fuera_de_limites": st.column_config.CheckboxColumn("Fuera de límites"),
                                "racha": st.column_config.CheckboxColumn("Racha")})
st.caption("Nota: las diferencias de eficiencia entre técnicos también generan variación; "
           "filtrar por técnico es una mejora sugerida para la v2.")
