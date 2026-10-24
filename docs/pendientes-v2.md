# Pendientes para la V2

Reconstruidos de la lista "Pendientes para la v2" entregada al cerrar la V1 (tag `v1-streamlit`)
y de las notas en el código (p. ej. el aviso de `8_Control_estadistico.py` sobre filtrar por técnico).
Todos se implementan en la V2.

| # | Pendiente de la V1 | Cómo se resuelve en la V2 | Estado |
|---|---|---|---|
| 1 | Probar la IA con una key real de Groq | Probado con key real; modelo por defecto `qwen/qwen3.8-27b` (llama-3.3 fue retirado) | ✅ |
| 2 | Gráfica de control filtrada por técnico | Filtro por técnico en `/api/spc/*` y en la vista de Control estadístico | ✅ |
| 3 | Gráfica X̄-R por subgrupos | `src/spc.py::xbar_r_chart` (constantes A2, D3, D4) + vista | ✅ |
| 4 | Número de observaciones necesarias del estudio de tiempos | `src/time_study.py::required_observations` (nivel de confianza y error) + calculadora | ✅ |
| 5 | Programación que respete la asignación actual y la disponibilidad de bahías | `src/sequencing.py::schedule_resources` (técnico asignado + bahía libre) | ✅ |
| 6 | Botón "reasignar" que aplique la propuesta de la secuenciación | `POST /api/sequencing/apply` (solo admin) actualiza técnico, bahía y fecha programada | ✅ |
| 7 | Inventario de refacciones con stock y punto de reorden | `src/inventory.py` (ROP = d̄·L + z·σd·√L), movimientos y consumo al terminar órdenes | ✅ |
| 8 | Cotización en PDF | `src/export.py::quote_to_pdf` (fpdf2, ligero) | ✅ |
| 9 | Persistencia en la nube | Ruta de la base configurable (`TALLER_DB_PATH`) para disco persistente + respaldo/restauración de la base desde Configuración | ✅ |
| 10 | Login sencillo | Login con bcrypt + JWT y permisos por rol validados en el backend | ✅ |
| 11 | Modo oscuro probado | Tema claro/oscuro con los mismos design tokens | ✅ |
