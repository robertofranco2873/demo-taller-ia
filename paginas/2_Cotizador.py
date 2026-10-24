from datetime import date, timedelta

import streamlit as st

from src import config, db
from src.ai.features import suggest_services, whatsapp_message
from src.ai.groq_client import AIError
from src.export import quote_to_excel
from src.workcalendar import add_workdays
from src.ui_common import ai_enabled, ai_unavailable_notice, money, setup_page

setup_page("Cotizador por fórmula", "🧾")
st.markdown("**Total** = [(horas estándar × tarifa) + refacciones] × (1 + margen) × (1 + IVA 16 %)")

services = db.load_services()
label_of = {r.code: f"{r.code} · {r.name}" for r in services.itertuples()}
code_of = {v: k for k, v in label_of.items()}
settings = db.get_settings()

with st.sidebar:
    st.markdown("**Parámetros de cotización**")
    rate = st.number_input("Tarifa por hora estándar (MXN)", 0.0, 5000.0, settings["labor_rate"], 10.0)
    margin = st.number_input("Margen (%)", 0.0, 200.0, settings["margin_pct"] * 100, 1.0) / 100
    if st.button("Guardar como predeterminados"):
        db.save_settings(rate, margin)
        st.success("Parámetros guardados.")

# ---------- IA: diagnóstico → servicios ----------
st.subheader("🤖 Diagnóstico a cotización (IA opcional)")
if ai_enabled():
    problem = st.text_area("Describe el problema del vehículo", placeholder="El carro hace ruido al frenar y vibra el volante")
    if st.button("Sugerir servicios del catálogo"):
        catalog = services[["code", "name", "category", "keywords"]].to_dict("records")
        try:
            with st.spinner("Consultando a la IA…"):
                result = suggest_services(problem, catalog)
            st.session_state.ai_diagnosis = result
            st.session_state.quote_sel = [label_of[s["codigo"]] for s in result["servicios"]]
            st.rerun()
        except AIError as e:
            st.error(str(e))
    result = st.session_state.get("ai_diagnosis")
    if result:
        if result["servicios"]:
            st.markdown("**Sugerencias (ya agregadas abajo; el precio lo calcula la fórmula):**")
            for s in result["servicios"]:
                st.markdown(f"- **{label_of[s['codigo']]}** — {s['motivo']} _(confianza {s['confianza']:.0%})_")
        else:
            st.warning("La IA no encontró servicios del catálogo para esa descripción.")
        if result["preguntas"]:
            st.markdown("**Preguntas sugeridas para el cliente:** " + " · ".join(result["preguntas"]))
        if result["descartados"]:
            st.caption(f"Códigos descartados por no existir en el catálogo: {', '.join(result['descartados'])}")
        if result["nota"]:
            st.caption(result["nota"])
else:
    ai_unavailable_notice()

# ---------- Cotización por fórmula ----------
st.subheader("Servicios a cotizar")
if "quote_sel" not in st.session_state:  # ejemplo inicial para el demo
    st.session_state.quote_sel = [label_of[c] for c in ("S03", "S08") if c in label_of]
selected = st.multiselect("Servicios del catálogo", list(code_of), key="quote_sel",
                          placeholder="Elige uno o más servicios")
qty = {}
if selected:
    cols = st.columns(min(len(selected), 4))
    for i, label in enumerate(selected):
        qty[label] = cols[i % len(cols)].number_input(f"Cantidad · {code_of[label]}", 1, 10, 1, key=f"qty_{code_of[label]}")

if not selected:
    st.info("Selecciona uno o más servicios para calcular la cotización.")
    st.stop()

sid_of = dict(zip(services["code"], services["id"]))
service_qty = {int(sid_of[code_of[l]]): q for l, q in qty.items()}
quote, _ = db.build_quote(service_qty, rate, margin)

st.dataframe(
    [{"Código": l.code, "Servicio": l.name, "Cant.": l.qty, "Horas estándar": round(l.hours, 2),
      "Mano de obra": l.labor(rate), "Refacciones": l.parts(), "Importe c/margen": quote.line_subtotal(l)}
     for l in quote.lines],
    hide_index=True, width="stretch",
    column_config={k: st.column_config.NumberColumn(format="$%.2f")
                   for k in ["Mano de obra", "Refacciones", "Importe c/margen"]},
)
c = st.columns(6)
c[0].metric("Horas estándar", f"{quote.hours:.2f} h")
c[1].metric("Mano de obra", money(quote.labor))
c[2].metric("Refacciones", money(quote.parts))
c[3].metric(f"Margen {margin:.0%}", money(quote.margin))
c[4].metric("IVA 16 %", money(quote.iva))
c[5].metric("TOTAL", money(quote.total))
st.caption(f"Subtotal = ({money(quote.labor)} + {money(quote.parts)}) × (1 + {margin:.0%}) = "
           f"{money(quote.subtotal)}".replace("$", "\\$"))

st.subheader("Cliente y salida")
a, b, c3 = st.columns(3)
customer = a.text_input("Cliente", "Cliente de prueba (ficticio)")
phone = b.text_input("Teléfono", "+52 55 0000 0000")
vehicle = c3.text_input("Vehículo", "Nissan Versa 2018")

x1, x2 = st.columns(2)
x1.download_button("📥 Exportar cotización a Excel", quote_to_excel(quote, customer, vehicle),
                   file_name=f"cotizacion_{date.today():%Y%m%d}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with x2.popover("🛠️ Convertir en orden de trabajo"):
    techs = db.load_technicians()
    bays = db.load_bays()
    tech = st.selectbox("Técnico", techs["name"].tolist())
    bay = st.selectbox("Bahía", bays["name"].tolist())
    sched = st.date_input("Fecha programada", date.today())
    due = st.date_input("Fecha compromiso", add_workdays(date.today(), max(1, int(quote.hours // 6) + 1)))
    if st.button("Crear orden", type="primary"):
        if (rate, margin) != (settings["labor_rate"], settings["margin_pct"]):
            db.save_settings(rate, margin)
        folio = db.create_order(customer, phone, vehicle, service_qty,
                                int(techs.loc[techs["name"] == tech, "id"].iloc[0]),
                                int(bays.loc[bays["name"] == bay, "id"].iloc[0]), due, sched)
        st.success(f"Orden {folio} creada. Revísala en la página Órdenes.")

if ai_enabled():
    st.subheader("💬 Mensaje de WhatsApp (IA)")
    if st.button("Redactar mensaje para el cliente"):
        try:
            with st.spinner("Redactando…"):
                st.session_state.whatsapp = whatsapp_message(
                    customer, vehicle, quote.as_dict(), [l.name for l in quote.lines], config.BUSINESS_NAME)
        except AIError as e:
            st.error(str(e))
    if st.session_state.get("whatsapp"):
        st.text_area("Mensaje (revísalo antes de enviarlo)", st.session_state.whatsapp, height=220)
        st.caption("Los importes provienen de la fórmula; verifica que la IA los haya copiado sin cambios.")
