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
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Grido_logo.svg/200px-Grido_logo.svg.png",
        width=130,
    )
    st.title("Grido Audit")

pg = st.navigation(
    [
        st.Page("pagina_captura.py", title="Captura de Fotos", icon="📸"),
        st.Page("pagina_auditoria.py", title="Auditoría IA", icon="🔍"),
    ]
)

pg.run()
