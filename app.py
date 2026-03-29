"""
Grido Audit Vision — Punto de entrada unificado.
Ejecutar con:  streamlit run app.py
"""

import streamlit as st

EJECUTIVO_PASSWORD = "1234"

st.set_page_config(
    page_title="Grido Audit Vision",
    page_icon="🍦",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "rol" not in st.session_state:
    st.session_state["rol"] = "operativo"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

with st.sidebar:
    st.image("logo.png", width=150)
    st.title("Grido Audit")

    st.divider()

    rol_selected = st.selectbox(
        "Rol",
        ["operativo", "ejecutivo"],
        index=["operativo", "ejecutivo"].index(st.session_state["rol"]),
        format_func=lambda r: "Operativo (Ivana)" if r == "operativo" else "Ejecutivo (Dirección)",
    )

    if rol_selected == "ejecutivo" and not st.session_state["authenticated"]:
        pwd = st.text_input("🔒 Contraseña Ejecutivo", type="password", key="exec_pwd")
        if st.button("Ingresar", use_container_width=True):
            if pwd == EJECUTIVO_PASSWORD:
                st.session_state["rol"] = "ejecutivo"
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        st.session_state["rol"] = "operativo"
    elif rol_selected == "operativo":
        st.session_state["rol"] = "operativo"
        st.session_state["authenticated"] = False
    else:
        st.session_state["rol"] = "ejecutivo"

    st.caption(f"👤 Sesión: **{'Ivana' if st.session_state['rol'] == 'operativo' else 'Dirección (Ejecutivo)'}**")

pg = st.navigation(
    [
        st.Page("pagina_captura.py", title="Captura de Fotos", icon="📸"),
        st.Page("pagina_auditoria.py", title="Auditoría IA", icon="🔍"),
        st.Page("pagina_mejoras.py", title="Planes de Mejora", icon="📊"),
        st.Page("pagina_historial.py", title="Historial", icon="📈"),
    ]
)

pg.run()
