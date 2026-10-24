from datetime import date

import streamlit as st

from src import config, db
from src.orders import next_status, time_variance
from src.workcalendar import add_workdays
from src.ui_common import money, setup_page

setup_page("Órdenes de trabajo", "🛠️")
st.caption("Flujo: recibida → en proceso → terminada → entregada. Al terminar se registra el tiempo real de cada servicio.")

orders = db.load_orders()
items = db.load_items()
services = db.load_services()
techs = db.load_technicians()
bays = db.load_bays()
tech_id = dict(zip(techs["name"], techs["id"]))
bay_id = dict(zip(bays["name"], bays["id"]))

counts = orders["status"].value_counts()
cols = st.columns(4)
for col, status in zip(cols, config.STATUSES):
    col.metric(status.capitalize(), int(counts.get(status, 0)))

tab_board, tab_update, tab_new, tab_hist = st.tabs(["📋 Tablero", "✏️ Actualizar orden", "➕ Nueva orden", "📚 Historial"])

with tab_board:
    active = orders[orders["status"] != "entregada"].copy()
    active["vencida"] = active["due_date"] < date.today()
    st.dataframe(
        active[["folio", "status", "customer", "vehicle", "technician", "bay", "scheduled_date",
                "due_date", "vencida", "std_hours", "total"]].sort_values(["status", "due_date"]),
        hide_index=True, width="stretch",
        column_config={
            "folio": "Folio", "status": "Estado", "customer": "Cliente", "vehicle": "Vehículo",
            "technician": "Técnico", "bay": "Bahía", "scheduled_date": "Programada",
            "due_date": "Compromiso", "vencida": st.column_config.CheckboxColumn("⚠ Vencida"),
            "std_hours": st.column_config.NumberColumn("Horas est.", format="%.2f"),
            "total": st.column_config.NumberColumn("Total", format="$%.2f"),
        })

with tab_update:
    open_orders = orders[orders["status"] != "entregada"].sort_values("created_at", ascending=False)
    if open_orders.empty:
        st.info("No hay órdenes abiertas.")
    else:
        options = {f"{r.folio} · {r.status} · {r.customer} · {r.vehicle}": r for r in open_orders.itertuples()}
        order = options[st.selectbox("Orden", list(options))]
        order_items = items[items["order_id"] == order.id]
        st.dataframe(order_items[["service_code", "service_name", "qty", "std_hours", "actual_hours", "line_subtotal"]],
                     hide_index=True, width="stretch",
                     column_config={"service_code": "Código", "service_name": "Servicio", "qty": "Cant.",
                                    "std_hours": st.column_config.NumberColumn("Horas est.", format="%.2f"),
                                    "actual_hours": st.column_config.NumberColumn("Horas reales", format="%.2f"),
                                    "line_subtotal": st.column_config.NumberColumn("Importe", format="$%.2f")})
        st.caption(f"Total con IVA: {money(order.total)} · Compromiso: {order.due_date}".replace("$", "\\$"))

        left, right = st.columns(2)
        with left:
            st.markdown("**Asignación**")
            new_tech = st.selectbox("Técnico", techs["name"].tolist(), index=techs["name"].tolist().index(order.technician))
            new_bay = st.selectbox("Bahía", bays["name"].tolist(), index=bays["name"].tolist().index(order.bay))
            new_sched = st.date_input("Fecha programada", order.scheduled_date)
            if st.button("Guardar asignación"):
                db.update_assignment(int(order.id), int(tech_id[new_tech]), int(bay_id[new_bay]), new_sched)
                st.success("Asignación actualizada.")
                st.rerun()
        with right:
            nxt = next_status(order.status)
            st.markdown(f"**Cambiar estado:** {order.status} → **{nxt}**")
            actual = {}
            if nxt == "terminada":
                st.caption("Registra el tiempo real (horas) de cada servicio:")
                for it in order_items.itertuples():
                    actual[int(it.id)] = st.number_input(f"{it.service_code} · {it.service_name}", 0.0, 100.0,
                                                         round(float(it.std_hours), 2), 0.05, key=f"act_{it.id}")
                total_actual = sum(actual.values())
                if total_actual > 0:
                    v = time_variance(float(order.std_hours), total_actual)
                    st.caption(f"Real {total_actual:.2f} h vs. estándar {order.std_hours:.2f} h → "
                               f"variación {v['variacion_pct']:+.0%}, eficiencia {v['eficiencia']:.0%}")
            if st.button(f"Pasar a «{nxt}»", type="primary"):
                try:
                    db.advance_order(int(order.id), nxt, actual or None)
                    st.success(f"Orden {order.folio}: {nxt}.")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

with tab_new:
    with st.form("new_order", clear_on_submit=True):
        a, b, c = st.columns(3)
        customer = a.text_input("Cliente *")
        phone = b.text_input("Teléfono")
        vehicle = c.text_input("Vehículo (marca, modelo, año)")
        labels = {f"{r.code} · {r.name} ({r.std_hours:.2f} h)": int(r.id) for r in services.itertuples()}
        chosen = st.multiselect("Servicios *", list(labels), placeholder="Elige servicios")
        a, b, c, d = st.columns(4)
        tech = a.selectbox("Técnico", techs["name"].tolist())
        bay = b.selectbox("Bahía", bays["name"].tolist())
        sched = c.date_input("Fecha programada", date.today())
        due = d.date_input("Fecha compromiso", add_workdays(date.today(), 2))
        notes = st.text_input("Notas")
        if st.form_submit_button("Crear orden", type="primary"):
            try:
                folio = db.create_order(customer, phone, vehicle, {labels[l]: 1 for l in chosen},
                                        int(tech_id[tech]), int(bay_id[bay]), due, sched, notes)
                st.success(f"Orden {folio} creada con precio calculado por fórmula.")
            except ValueError as e:
                st.error(str(e))

with tab_hist:
    done = orders[orders["actual_hours"].notna()].copy()
    done["eficiencia"] = done["std_hours"] / done["actual_hours"]
    done["variacion"] = done["actual_hours"] / done["std_hours"] - 1
    tech_filter = st.multiselect("Filtrar por técnico", techs["name"].tolist(), placeholder="Todos")
    if tech_filter:
        done = done[done["technician"].isin(tech_filter)]
    st.dataframe(
        done[["folio", "created_at", "status", "customer", "technician", "bay", "std_hours", "actual_hours",
              "eficiencia", "variacion", "total"]].sort_values("created_at", ascending=False),
        hide_index=True, width="stretch",
        column_config={
            "folio": "Folio", "created_at": st.column_config.DatetimeColumn("Recepción", format="YYYY-MM-DD HH:mm"),
            "status": "Estado", "customer": "Cliente", "technician": "Técnico", "bay": "Bahía",
            "std_hours": st.column_config.NumberColumn("Estándar (h)", format="%.2f"),
            "actual_hours": st.column_config.NumberColumn("Real (h)", format="%.2f"),
            "eficiencia": st.column_config.NumberColumn("Eficiencia", format="percent"),
            "variacion": st.column_config.NumberColumn("Real vs. est.", format="percent"),
            "total": st.column_config.NumberColumn("Total", format="$%.2f"),
        })
