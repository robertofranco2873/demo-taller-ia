import pandas as pd
import streamlit as st

from src import db
from src.time_study import normal_time, observed_average, standard_time
from src.ui_common import money, setup_page

setup_page("Catálogo y estudio de tiempos", "🧰")
st.markdown(
    "**Tiempo normal** = tiempo observado promedio × factor de calificación  \n"
    "**Tiempo estándar** = tiempo normal × (1 + % suplementos)"
)

services = db.load_services()

st.subheader("Catálogo de servicios (editable)")
st.caption("Edita nombre, categoría, minutos observados, factor de calificación o suplementos y guarda. "
           "Los tiempos normal y estándar se recalculan con las fórmulas.")
view = services[["id", "code", "name", "category", "observed_avg_min", "rating_factor", "allowance_pct",
                 "normal_min", "standard_min", "std_hours", "parts_cost"]].copy()
view["allowance_pct"] = view["allowance_pct"] * 100
edited = st.data_editor(
    view, hide_index=True, width="stretch", key="catalog_editor",
    disabled=["id", "code", "normal_min", "standard_min", "std_hours", "parts_cost"],
    column_config={
        "id": None,
        "code": st.column_config.TextColumn("Código"),
        "name": st.column_config.TextColumn("Servicio", width="medium"),
        "category": st.column_config.TextColumn("Categoría"),
        "observed_avg_min": st.column_config.NumberColumn("T. observado (min)", min_value=1.0, format="%.1f"),
        "rating_factor": st.column_config.NumberColumn("Factor calif.", min_value=0.5, max_value=1.5, step=0.01, format="%.2f"),
        "allowance_pct": st.column_config.NumberColumn("Suplementos %", min_value=0.0, max_value=100.0, format="%.0f"),
        "normal_min": st.column_config.NumberColumn("T. normal (min)", format="%.1f"),
        "standard_min": st.column_config.NumberColumn("T. estándar (min)", format="%.1f"),
        "std_hours": st.column_config.NumberColumn("Horas estándar", format="%.2f"),
        "parts_cost": st.column_config.NumberColumn("Refacciones", format="$%.2f"),
    },
)
if st.button("💾 Guardar cambios del catálogo", type="primary"):
    changed, errors = 0, []
    original = view.set_index("id")
    for row in edited.itertuples():
        o = original.loc[row.id]
        if (row.name, row.category, row.observed_avg_min, row.rating_factor, row.allowance_pct) != \
                (o["name"], o["category"], o["observed_avg_min"], o["rating_factor"], o["allowance_pct"]):
            try:
                db.update_service(int(row.id), row.name, row.category, float(row.observed_avg_min),
                                  float(row.rating_factor), float(row.allowance_pct) / 100)
                changed += 1
            except (ValueError, TypeError) as e:
                errors.append(f"{row.code}: {e}")
    for e in errors:
        st.error(e)
    if changed:
        st.success(f"{changed} servicio(s) actualizado(s).")
        st.rerun()
    elif not errors:
        st.info("No hubo cambios.")

st.divider()
left, right = st.columns(2)

with left:
    st.subheader("🧮 Calculadora de estudio de tiempos")
    labels = {f"{r.code} · {r.name}": r for r in services.itertuples()}
    choice = st.selectbox("Servicio", list(labels))
    svc = labels[choice]
    obs_text = st.text_area("Tiempos observados (min), separados por coma",
                            "", placeholder=f"p. ej. {svc.observed_avg_min:.0f}, {svc.observed_avg_min * 1.1:.0f}, "
                                            f"{svc.observed_avg_min * 0.95:.0f}")
    rf = st.slider("Factor de calificación (desempeño del operario)", 0.70, 1.30, float(svc.rating_factor), 0.01)
    allowance = st.slider("Suplementos (%)", 0, 40, int(round(svc.allowance_pct * 100))) / 100
    try:
        values = [float(x) for x in obs_text.replace(";", ",").split(",") if x.strip()]
        avg = observed_average(values) if values else float(svc.observed_avg_min)
        tn = normal_time(avg, rf)
        ts = standard_time(tn, allowance)
        a, b, c = st.columns(3)
        a.metric("T. observado prom.", f"{avg:.1f} min", f"{len(values)} obs." if values else "actual", delta_color="off")
        b.metric("Tiempo normal", f"{tn:.1f} min")
        c.metric("Tiempo estándar", f"{ts:.1f} min", f"{ts / 60:.2f} h", delta_color="off")
        st.caption(f"TN = {avg:.1f} × {rf:.2f} = {tn:.1f} min · TS = {tn:.1f} × (1 + {allowance:.0%}) = {ts:.1f} min")
        if st.button("Aplicar al catálogo"):
            db.update_service(int(svc.id), svc.name, svc.category, avg, rf, allowance)
            st.success("Servicio actualizado.")
            st.rerun()
    except ValueError as e:
        st.error(f"Revisa los datos: {e}")

with right:
    st.subheader("🔩 Refacciones del servicio")
    parts = db.load_service_parts(int(svc.id))
    if parts.empty:
        st.info("Este servicio no lleva refacciones (solo mano de obra).")
    else:
        st.dataframe(parts.rename(columns={"code": "Código", "name": "Refacción", "qty": "Cant.",
                                           "price": "Precio", "importe": "Importe"}),
                     hide_index=True, width="stretch",
                     column_config={"Precio": st.column_config.NumberColumn(format="$%.2f"),
                                    "Importe": st.column_config.NumberColumn(format="$%.2f")})
        st.metric("Costo de refacciones", money(parts["importe"].sum()))

st.divider()
c1, c2 = st.columns(2)
with c1:
    with st.expander("➕ Agregar servicio al catálogo"):
        with st.form("new_service", clear_on_submit=True):
            code = st.text_input("Código", f"S{len(services) + 1:02d}")
            name = st.text_input("Nombre")
            category = st.text_input("Categoría", "Mantenimiento")
            obs = st.number_input("Tiempo observado promedio (min)", 1.0, 2000.0, 60.0)
            rf_new = st.number_input("Factor de calificación", 0.5, 1.5, 1.0, 0.01)
            allow_new = st.number_input("Suplementos (%)", 0.0, 100.0, 15.0) / 100
            kw = st.text_input("Síntomas / palabras clave (ayudan a la IA)")
            if st.form_submit_button("Agregar"):
                try:
                    if not name.strip():
                        raise ValueError("El nombre es obligatorio.")
                    db.add_service(code.strip(), name.strip(), category.strip(), obs, rf_new, allow_new, kw)
                    st.success("Servicio agregado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo agregar: {e}")
with c2:
    with st.expander("💲 Precios de refacciones"):
        all_parts = db.load_parts()
        edited_parts = st.data_editor(all_parts, hide_index=True, width="stretch",
                                      disabled=["id", "code", "name"], key="parts_editor",
                                      column_config={"id": None,
                                                     "price": st.column_config.NumberColumn("Precio", min_value=0.0, format="$%.2f")})
        if st.button("Guardar precios"):
            diff = edited_parts[edited_parts["price"] != all_parts["price"]]
            for r in diff.itertuples():
                db.update_part_price(int(r.id), float(r.price))
            st.success(f"{len(diff)} precio(s) actualizado(s).")
            if len(diff):
                st.rerun()
