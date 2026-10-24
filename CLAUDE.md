# CLAUDE.md — demo-taller-ia

App demo (Streamlit + SQLite) de un taller mecánico **ficticio** ("AutoServicio Demo").

## Reglas
- Todo es DEMO con datos ficticios: mantener el aviso en la UI, README y exportables.
- Lógica de negocio en `src/` como funciones puras, sin `import streamlit`
  (única excepción: `src/ui_common.py`). Las páginas en `paginas/` solo muestran (registradas en `app.py` con `st.navigation`;
  no renombrar a `pages/`, Streamlit la autodetecta y duplica el menú).
- Toda fórmula nueva lleva prueba en `tests/`. Correr `.\.venv\Scripts\python.exe -m pytest -q`
  antes de cada commit; `tests/test_pages.py` ejecuta cada página con `AppTest`.
- La IA (Groq, `src/ai/`) solo interpreta texto y redacta. **Nunca** calcula precios ni
  métricas; recibe números ya calculados. Sus respuestas JSON se validan contra el catálogo.
- La app debe funcionar completa sin `GROQ_API_KEY` (ocultar funciones de IA con aviso).
- Errores de Groq (401, 429, timeout) se convierten en `AIError` con mensaje claro.
- Dependencias ligeras (PC de bajos recursos): no agregar frameworks pesados ni modelos locales.
- Gráficas en `src/charts.py`: un solo eje por gráfica, colores por función, tooltips.
- Windows + PowerShell, Python 3.12 en `.venv`. Textos de UI en español.
- `data/taller.db` no se versiona; se regenera con `python -m src.seed` (semilla 42).
