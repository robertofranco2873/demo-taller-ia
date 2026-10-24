"""AutoServicio Demo (datos ficticios). Ejecuta:  streamlit run app.py"""
import streamlit as st

PAGES = [
    st.Page("pages/0_Inicio.py", title="Inicio", icon="🔧", default=True),
    st.Page("pages/1_Catalogo_y_tiempos.py", title="Catálogo y tiempos", icon="🧰", url_path="catalogo"),
    st.Page("pages/2_Cotizador.py", title="Cotizador", icon="🧾", url_path="cotizador"),
    st.Page("pages/3_Ordenes.py", title="Órdenes", icon="🛠️", url_path="ordenes"),
    st.Page("pages/4_Dashboard.py", title="Dashboard", icon="📊", url_path="dashboard"),
    st.Page("pages/5_Pareto.py", title="Pareto", icon="📈", url_path="pareto"),
    st.Page("pages/6_Capacidad.py", title="Capacidad", icon="⚖️", url_path="capacidad"),
    st.Page("pages/7_Secuenciacion.py", title="Secuenciación", icon="🗓️", url_path="secuenciacion"),
    st.Page("pages/8_Control_estadistico.py", title="Control estadístico", icon="🎯", url_path="control"),
]

st.navigation(PAGES).run()
