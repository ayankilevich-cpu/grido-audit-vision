"""
Grido Audit Vision — Punto de entrada unificado.
Ejecutar con:  streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Grido Audit Vision",
    page_icon="🍦",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    st.image("logo.png", width=150)
    st.title("Grido Audit")

    st.divider()
    if "rol" not in st.session_state:
        st.session_state["rol"] = "operativo"
    st.session_state["rol"] = st.selectbox(
        "Rol",
        ["operativo", "ejecutivo"],
        index=["operativo", "ejecutivo"].index(st.session_state["rol"]),
        format_func=lambda r: "Operativo (Romina)" if r == "operativo" else "Ejecutivo (Dirección)",
    )

pg = st.navigation(
    [
        st.Page("pagina_captura.py", title="Captura de Fotos", icon="📸"),
        st.Page("pagina_auditoria.py", title="Auditoría IA", icon="🔍"),
        st.Page("pagina_mejoras.py", title="Planes de Mejora", icon="📊"),
        st.Page("pagina_historial.py", title="Historial", icon="📈"),
    ]
)

pg.run()
