"""Gráficas Plotly. Un solo eje por gráfica; color por función (serie, estado, referencia)."""
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.workcalendar import add_work_hours

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
PRIMARY = SERIES[0]
SECONDARY = SERIES[1]
GOOD = "#0ca30c"
CRITICAL = "#d03b3b"
MUTED = "#898781"


def _layout(fig: go.Figure, title: str, y_title: str = "", x_title: str = "", height: int = 380) -> go.Figure:
    fig.update_layout(title=title, height=height, margin=dict(l=10, r=10, t=50, b=10),
                      xaxis_title=x_title, yaxis_title=y_title, hovermode="closest",
                      bargap=0.25,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.update_traces(selector=dict(type="bar"), marker_line_width=0)
    return fig


def revenue_by_month(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Bar(x=df["mes"], y=df["ingresos"], marker_color=PRIMARY,
                           customdata=df["ordenes"],
                           hovertemplate="%{x|%b %Y}<br>Ingresos: $%{y:,.0f}<br>Órdenes: %{customdata}<extra></extra>"))
    fig.update_xaxes(dtick="M1", tickformat="%b %Y")
    return _layout(fig, "Ingresos por mes (con IVA)", "MXN")


def efficiency_by_technician(df: pd.DataFrame) -> go.Figure:
    colors = [PRIMARY if e >= 1 else SECONDARY for e in df["eficiencia"]]
    fig = go.Figure(go.Bar(x=df["technician"], y=df["eficiencia"], marker_color=colors,
                           text=[f"{e:.0%}" for e in df["eficiencia"]], textposition="outside",
                           customdata=df[["std_hours", "actual_hours"]],
                           hovertemplate="%{x}<br>Eficiencia: %{y:.1%}<br>Estándar: %{customdata[0]:.1f} h"
                                         "<br>Real: %{customdata[1]:.1f} h<extra></extra>"))
    fig.add_hline(y=1, line_dash="dash", line_color=MUTED, annotation_text="100 % = estándar")
    fig.update_yaxes(tickformat=".0%", range=[0, max(1.3, df["eficiencia"].max() * 1.15) if len(df) else 1.3])
    return _layout(fig, "Eficiencia por técnico (estándar / real)")


def bay_utilization(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Bar(x=df["bay"], y=df["utilizacion"], marker_color=PRIMARY,
                           text=[f"{u:.0%}" for u in df["utilizacion"]], textposition="outside",
                           customdata=df[["horas_usadas", "horas_disponibles"]],
                           hovertemplate="%{x}<br>Utilización: %{y:.1%}<br>Usadas: %{customdata[0]:.0f} h"
                                         "<br>Disponibles: %{customdata[1]:.0f} h<extra></extra>"))
    fig.update_yaxes(tickformat=".0%", range=[0, 1.05])
    return _layout(fig, "Utilización de bahías (horas usadas / disponibles)")


def pareto(table: pd.DataFrame, category_col: str, value_label: str) -> go.Figure:
    """Barras = % de cada categoría; línea = % acumulado. Ambos en el mismo eje (0-100 %)."""
    colors = [PRIMARY if c == "A" else "#86b6ef" for c in table["clase"]]
    fig = go.Figure()
    fig.add_bar(x=table[category_col], y=table["pct"], name="% del total", marker_color=colors,
                customdata=table["valor"],
                hovertemplate="%{x}<br>" + value_label + ": %{customdata:,.0f}<br>% del total: %{y:.1%}<extra></extra>")
    fig.add_scatter(x=table[category_col], y=table["pct_acumulado"], name="% acumulado",
                    mode="lines+markers", line=dict(color=SECONDARY, width=2), marker=dict(size=8),
                    hovertemplate="%{x}<br>Acumulado: %{y:.1%}<extra></extra>")
    fig.add_hline(y=0.8, line_dash="dash", line_color=MUTED, annotation_text="80 %")
    fig.update_yaxes(tickformat=".0%", range=[0, 1.05])
    fig.update_xaxes(tickangle=-40)
    return _layout(fig, f"Pareto de servicios por {value_label.lower()}", height=480)


def load_vs_capacity(df: pd.DataFrame) -> go.Figure:
    colors = [CRITICAL if o else PRIMARY for o in df["sobrecarga"]]
    fig = go.Figure(go.Bar(x=df["technician"], y=df["carga_horas"], marker_color=colors, name="Carga",
                           text=[f"{u:.0%}{' ⚠ sobrecarga' if o else ''}" for u, o in zip(df["utilizacion"], df["sobrecarga"])],
                           textposition="outside",
                           customdata=df[["capacidad_horas", "ordenes"]],
                           hovertemplate="%{x}<br>Carga: %{y:.1f} h<br>Capacidad: %{customdata[0]:.0f} h"
                                         "<br>Órdenes: %{customdata[1]}<extra></extra>"))
    cap = float(df["capacidad_horas"].iloc[0]) if len(df) else 0
    fig.add_hline(y=cap, line_dash="dash", line_color=MUTED, annotation_text=f"Capacidad {cap:.0f} h")
    fig.update_yaxes(range=[0, max(cap, df["carga_horas"].max() if len(df) else 0) * 1.25 or 1])
    return _layout(fig, "Horas estándar programadas vs. capacidad", "Horas")


def gantt(schedule_df: pd.DataFrame, now: datetime, title: str) -> go.Figure:
    """Convierte horas laborables a fechas reales con el calendario del taller."""
    df = schedule_df.copy()
    df["Inicio"] = [add_work_hours(now, h) for h in df["inicio_h"]]
    df["Fin"] = [add_work_hours(now, h) for h in df["fin_h"]]
    df["Estado"] = ["Tarde" if t else "A tiempo" for t in df["tarde"]]
    fig = px.timeline(df, x_start="Inicio", x_end="Fin", y="recurso", color="Estado", text="orden",
                      color_discrete_map={"A tiempo": PRIMARY, "Tarde": CRITICAL},
                      hover_data={"orden": True, "proceso_h": ":.1f", "retraso_h": ":.1f",
                                  "recurso": False, "Estado": True})
    fig.update_yaxes(autorange="reversed", title="")
    fig.update_traces(marker_line_color="rgba(255,255,255,0.9)", marker_line_width=2)
    return _layout(fig, title, height=max(300, 90 * df["recurso"].nunique() + 120))


def control_chart(df: pd.DataFrame, limits: dict, title: str) -> go.Figure:
    abnormal = df["fuera_de_limites"] | df["racha"]
    fig = go.Figure()
    fig.add_scatter(x=df["n"], y=df["valor"], mode="lines+markers", name="Tiempo real",
                    line=dict(color=PRIMARY, width=2), marker=dict(size=8, color=PRIMARY),
                    customdata=df[["folio", "technician"]] if "folio" in df else None,
                    hovertemplate="Muestra %{x}<br>%{y:.2f} h" +
                                  ("<br>%{customdata[0]} · %{customdata[1]}" if "folio" in df else "") +
                                  "<extra></extra>")
    fig.add_scatter(x=df.loc[abnormal, "n"], y=df.loc[abnormal, "valor"], mode="markers",
                    name="Señal anormal", marker=dict(size=12, color=CRITICAL, symbol="x"),
                    hoverinfo="skip")
    for key, label, dash in [("lsc", "LSC", "dash"), ("lc", "LC", "solid"), ("lic", "LIC", "dash")]:
        fig.add_hline(y=limits[key], line_dash=dash, line_color=MUTED if key == "lc" else CRITICAL,
                      line_width=1.5, annotation_text=f"{label} {limits[key]:.2f} h",
                      annotation_position="top left")
    return _layout(fig, title, "Horas reales", "Muestra (orden cronológico)", height=430)
