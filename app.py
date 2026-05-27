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
st.markdown(
    """
<style>
/* Padding para que el contenido no quede tapado por la barra */
.block-container {
    padding-bottom: 80px !important;
}

/* Barra inferior fija */
.nav-bottom {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 9999;
    background: #0033CC;
    display: flex;
    justify-content: space-around;
    align-items: center;
    height: 64px;
    border-top: 2px solid #E63329;
    box-shadow: 0 -2px 12px rgba(0,51,204,0.35);
}

/* Links dentro de la barra */
.nav-bottom a {
    color: rgba(255,255,255,0.75) !important;
    text-decoration: none !important;
    display: flex;
    flex-direction: column;
    align-items: center;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 8px 16px;
    border-radius: 8px;
    transition: all 0.2s;
    min-width: 64px;
    text-align: center;
}

.nav-bottom a:hover {
    color: white !important;
    background: rgba(230, 51, 41, 0.25);
}

.nav-bottom a .nav-icon {
    font-size: 1.3rem;
    line-height: 1;
    margin-bottom: 2px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Barra de navegación inferior ────────────────────────────────────────
st.markdown(
    """
<div class="nav-bottom">
  <a href="/pagina_captura">
    <span class="nav-icon">📸</span>Captura
  </a>
  <a href="/pagina_auditoria">
    <span class="nav-icon">🔍</span>Auditar
  </a>
  <a href="/pagina_mejoras">
    <span class="nav-icon">📊</span>Mejoras
  </a>
  <a href="/pagina_historial">
    <span class="nav-icon">📈</span>Historial
  </a>
</div>
""",
    unsafe_allow_html=True,
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
