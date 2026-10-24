"""Utilidades compartidas por las páginas de Streamlit (única capa que importa streamlit)."""
from datetime import date

import pandas as pd
import streamlit as st

from src import config, db
from src.ai.groq_client import get_api_key


def setup_page(title: str, icon: str = "🔧") -> None:
    st.set_page_config(page_title=f"{title} · {config.BUSINESS_NAME}", page_icon=icon, layout="wide")
    if "db_ready" not in st.session_state:
        if db.ensure_database():
            st.toast("Base de datos demo creada con datos ficticios.")
        st.session_state.db_ready = True
    with st.sidebar:
        st.markdown(f"**{config.BUSINESS_NAME}**")
        st.caption(config.DEMO_NOTICE)
        st.caption("🤖 IA: " + ("activa (Groq)" if ai_enabled() else "desactivada (sin GROQ_API_KEY)"))
    st.title(f"{icon} {title}")


def demo_banner() -> None:
    st.warning(config.DEMO_NOTICE)


def ai_enabled() -> bool:
    return get_api_key() is not None


def ai_unavailable_notice() -> None:
    st.info("🤖 Las funciones de IA están desactivadas porque no hay `GROQ_API_KEY`. "
            "Todo lo demás funciona igual. Para activarlas, copia `.env.example` a `.env` y "
            "agrega tu key gratuita de console.groq.com.")


def date_filter(orders: pd.DataFrame, key: str) -> tuple[date, date]:
    """Selector de rango de fechas en la barra lateral (por fecha de recepción)."""
    min_d = orders["created_at"].min().date()
    max_d = orders["created_at"].max().date()
    with st.sidebar:
        st.markdown("**Filtro de fechas** (recepción)")
        value = st.date_input("Rango", (min_d, max_d), min_value=min_d, max_value=max_d, key=key)
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return value[0], value[1]
    return min_d, max_d


def money(x: float) -> str:
    return f"${x:,.2f}"


def money_short(x: float) -> str:
    """Monto compacto para tarjetas KPI: $1.72 M, $45.3 k."""
    if abs(x) >= 1_000_000:
        return f"${x / 1_000_000:.2f} M"
    if abs(x) >= 10_000:
        return f"${x / 1_000:.1f} k"
    return money(x)
