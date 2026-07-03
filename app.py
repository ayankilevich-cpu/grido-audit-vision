"""
Grido Audit Vision — Punto de entrada unificado.
Ejecutar con:  streamlit run app.py
"""

import streamlit as st

EJECUTIVO_PASSWORD = st.secrets.get("EXEC_PASSWORD", "1234")

st.set_page_config(
    page_title="Grido Audit Vision",
    page_icon="🍦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS: barra de navegación inferior fija ──────────────────────────────
# Nota: la barra usa botones reales de Streamlit + st.switch_page (no <a href>
# con navegación de navegador), porque los links crudos abrían una pestaña
# nueva en vez de moverse dentro de la misma app (sobre todo en tablets).
st.markdown(
    """
<style>
/* Padding para que el contenido no quede tapado por la barra */
.block-container {
    padding-bottom: 90px !important;
}

/* Barra inferior fija */
.st-key-bottom_nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 9999;
    background: #0033CC;
    border-top: 2px solid #E63329;
    box-shadow: 0 -2px 12px rgba(0,51,204,0.35);
    padding: 6px 8px 2px 8px;
}

.st-key-bottom_nav div[data-testid="stHorizontalBlock"] {
    gap: 4px;
}

/* Botones dentro de la barra, con look de link */
.st-key-bottom_nav .stButton > button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: rgba(255,255,255,0.8) !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    line-height: 1.3 !important;
    white-space: pre-line !important;
    border-radius: 8px !important;
    padding: 6px 4px !important;
    min-height: 44px !important;
}

.st-key-bottom_nav .stButton > button:hover {
    color: white !important;
    background: rgba(230, 51, 41, 0.25) !important;
    border: none !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Barra de navegación inferior ────────────────────────────────────────
with st.container(key="bottom_nav"):
    _nav_c1, _nav_c2, _nav_c3, _nav_c4 = st.columns(4)
    with _nav_c1:
        if st.button("📸\nCaptura", key="nav_btn_captura", use_container_width=True):
            st.switch_page("pagina_captura.py")
    with _nav_c2:
        if st.button("🔍\nAuditar", key="nav_btn_auditar", use_container_width=True):
            st.switch_page("pagina_auditoria.py")
    with _nav_c3:
        if st.button("📊\nMejoras", key="nav_btn_mejoras", use_container_width=True):
            st.switch_page("pagina_mejoras.py")
    with _nav_c4:
        if st.button("📈\nHistorial", key="nav_btn_historial", use_container_width=True):
            st.switch_page("pagina_historial.py")

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
        st.Page("pagina_auditoria.py", title="Auditoría", icon="🔍"),
        st.Page("pagina_mejoras.py", title="Planes de Mejora", icon="📊"),
        st.Page("pagina_historial.py", title="Historial", icon="📈"),
    ]
)

pg.run()
