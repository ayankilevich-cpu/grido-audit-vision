"""
Grido Fotos — Captura de fotos y evaluación de auditoría, en un solo paso.
Guarda fotos comprimidas en MongoDB Atlas (o session_state como fallback) y,
para el mismo ítem, el estado Conforme/Observación/No Conforme.
"""

from __future__ import annotations

import io
import zipfile
from datetime import date, datetime

import streamlit as st
from PIL import Image

from criteria import CRITERIA, LOCALES, SECTIONS, TIPOS_AUDITORIA, get_criteria_by_section
import db

# ── Constantes ────────────────────────────────────────────────────────────

MAX_DIM = 1200
JPEG_QUALITY = 80

NO_PHOTO_ITEMS = {"C.17"}

STATUS_ICONS = {
    "Conforme": "✅",
    "Observación": "⚠️",
    "No Conforme": "❌",
}
STATUSES = ["Conforme", "Observación", "No Conforme"]

SECTION_FOLDERS = {
    "A": "A_Infraestructura",
    "B": "B_Experiencia",
    "C": "C_Operatoria",
    "D": "D_Imagen",
    "E": "E_Stock",
}

SECTION_SHORT = {
    "A": "Infraestructura",
    "B": "Experiencia",
    "C": "Operatoria",
    "D": "Imagen",
    "E": "Stock",
}

# ── CSS ───────────────────────────────────────────────────────────────────

st.markdown(
    """
<style>
/* Touch targets — pensados para dedo en tablet, no para mouse */
.stButton>button {
    min-height: 52px !important;
    font-size: 1.05rem !important;
}
div[data-testid="stSelectbox"] > div > div {
    min-height: 52px !important;
    font-size: 1.05rem !important;
}
div[data-testid="stTextArea"] textarea {
    font-size: 1.05rem !important;
    min-height: 90px !important;
}
div[data-testid="stFileUploader"] label {
    min-height: 48px !important;
    font-size: 1rem !important;
}
div[data-testid="stExpander"] summary {
    min-height: 50px !important;
    font-size: 1rem !important;
}
/* Métricas de progreso */
div[data-testid="stMetric"] {
    background: #f8f9fa;
    border-radius: 8px;
    padding: .5rem;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,.08);
}
div[data-testid="stMetric"] label { font-size: .8rem !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.15rem !important; }
/* Más espaciado entre elementos en tablet */
.block-container { padding-top: 1.5rem !important; }

/* Tarjetas que agrupan cada bloque de la pantalla (en vez de líneas finas) */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07);
}

/* Tarjetas grandes de estado (Conforme / Observación / No Conforme) */
div[class*="st-key-cap_btn_conforme_"] button {
    background: #2ecc71 !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    min-height: 60px !important;
    border-radius: 10px !important;
}
div[class*="st-key-cap_btn_observacion_"] button {
    background: #f39c12 !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    min-height: 60px !important;
    border-radius: 10px !important;
}
div[class*="st-key-cap_btn_noconforme_"] button {
    background: #e74c3c !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    min-height: 60px !important;
    border-radius: 10px !important;
}
div[class*="_unsel"] button {
    opacity: 0.42 !important;
}
div[class*="_sel"] button {
    opacity: 1 !important;
    box-shadow: 0 0 0 3px rgba(0,0,0,0.35) inset !important;
}
</style>""",
    unsafe_allow_html=True,
)

# ── Session state fallback ────────────────────────────────────────────────

if "cap_photos" not in st.session_state:
    st.session_state.cap_photos: dict[str, list[dict]] = {}

use_mongo = db.is_connected()


# ── Helpers ───────────────────────────────────────────────────────────────


def compress_photo(uploaded_file) -> bytes:
    """Compress an uploaded image and return JPEG bytes."""
    try:
        img = Image.open(uploaded_file)
    except Exception:
        return uploaded_file.getvalue()

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    w, h = img.size
    if max(w, h) > MAX_DIM:
        ratio = MAX_DIM / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


def _photo_count(local: str, fecha: str, item_id: str) -> int:
    if use_mongo:
        counts = _get_counts(local, fecha)
        return counts.get(item_id, 0)
    return len(st.session_state.cap_photos.get(item_id, []))


@st.cache_data(ttl=5)
def _get_counts(local: str, fecha: str) -> dict[str, int]:
    return db.get_photo_counts(local, fecha)


def _total_photos(local: str, fecha: str) -> int:
    if use_mongo:
        return sum(_get_counts(local, fecha).values())
    return sum(len(v) for v in st.session_state.cap_photos.values())


def _total_size_str(local: str, fecha: str) -> str:
    if use_mongo:
        total = db.get_total_size(local, fecha)
    else:
        total = sum(
            len(p["data"])
            for photos in st.session_state.cap_photos.values()
            for p in photos
        )
    if total < 1024 * 1024:
        return f"{total / 1024:.0f} KB"
    return f"{total / (1024 * 1024):.1f} MB"


def _build_zip(local: str, fecha: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if use_mongo:
            all_photos = db.get_all_photos(local, fecha)
            for p in all_photos:
                sec = p["section"]
                code = p["item_id"].replace(".", "")
                path = f"{SECTION_FOLDERS[sec]}/{code}/{p['photo_name']}"
                zf.writestr(path, p["photo_data"])
        else:
            for item_id, photos in st.session_state.cap_photos.items():
                sec = item_id[0]
                code = item_id.replace(".", "")
                for p in photos:
                    path = f"{SECTION_FOLDERS[sec]}/{code}/{p['name']}"
                    zf.writestr(path, p["data"])

        summary = _build_summary(local, fecha)
        zf.writestr("resumen.txt", summary)

    return buf.getvalue()


def _build_summary(local: str, fecha: str) -> str:
    lines = [
        "AUDITORÍA — FOTOS CAPTURADAS",
        f"Local: {local or 'Sin especificar'}",
        f"Fecha: {fecha}",
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Fotos totales: {_total_photos(local, fecha)}",
        f"Tamaño: {_total_size_str(local, fecha)}",
        f"Almacenamiento: {'MongoDB Atlas' if use_mongo else 'Sesión local'}",
        "",
        "DETALLE POR ÍTEM:",
    ]
    for c in CRITERIA:
        n = _photo_count(local, fecha, c["id"])
        if c["id"] in NO_PHOTO_ITEMS:
            flag = "⏭️"
        elif n > 0:
            flag = "✅"
        else:
            flag = "❌"
        lines.append(f"  {flag} {c['id']}: {n} fotos")
    return "\n".join(lines)


# ── Evaluación (Conforme / Observación / No Conforme) ──────────────────────


@st.cache_data(ttl=5)
def _get_eval_map(local: str, fecha: str) -> dict[str, dict]:
    """Devuelve {item_id: último resultado guardado} para precargar el estado."""
    if not use_mongo:
        return {}
    results = db.get_audit_results(local, fecha)
    m: dict[str, dict] = {}
    for r in results:
        m[r["item_id"]] = r  # ordenado por analyzed_at asc → el último gana
    return m


def _persist_evaluation(
    local: str, fecha: str, section: str, item: dict, status: str, nota: str, tipo_auditoria: str
) -> bool:
    """Guarda la evaluación manual del ítem (y crea desvío si corresponde)."""
    if not use_mongo:
        return False
    try:
        db.save_audit_result(
            local=local,
            fecha=fecha,
            section=section,
            item_id=item["id"],
            item_name=item["name"],
            result={
                "status": status,
                "justificacion": nota.strip(),
                "detalles_observados": [],
                "recomendaciones": [],
            },
            filename="captura",
            model="manual",
        )
        if status != "Conforme":
            nivel = "rojo" if status == "No Conforme" else "amarillo"
            prioridad = "alta" if status == "No Conforme" else "media"
            db.create_desvio(
                auditoria_fecha=fecha,
                local=local,
                seccion=item["section"],
                item_codigo=item["id"],
                item_descripcion=item["name"][:120],
                nivel=nivel,
                ai_justificacion=nota.strip(),
                prioridad=prioridad,
            )
        db.upsert_auditoria(
            local=local,
            fecha=fecha,
            tipo=tipo_auditoria,
            created_by=st.session_state.get("rol", "operativo"),
        )
        _get_eval_map.clear()
        return True
    except Exception as e:
        st.warning(f"No se pudo guardar la evaluación: {e}")
        return False


def _cap_advance() -> bool:
    """Navega al siguiente ítem de la lista completa (cruza secciones)."""
    ids = [c["id"] for c in CRITERIA]
    cur = st.session_state.get("cap_item")
    cur_id = cur["id"] if cur else ids[0]
    idx = ids.index(cur_id) if cur_id in ids else -1
    if 0 <= idx < len(ids) - 1:
        nxt = CRITERIA[idx + 1]
        st.session_state["_cap_nav_section"] = nxt["section"]
        st.session_state["_cap_nav_item"] = nxt["id"]
        return True
    return False


def _cap_retreat() -> bool:
    """Navega al ítem anterior de la lista completa (cruza secciones)."""
    ids = [c["id"] for c in CRITERIA]
    cur = st.session_state.get("cap_item")
    cur_id = cur["id"] if cur else ids[0]
    idx = ids.index(cur_id) if cur_id in ids else -1
    if idx > 0:
        prev = CRITERIA[idx - 1]
        st.session_state["_cap_nav_section"] = prev["section"]
        st.session_state["_cap_nav_item"] = prev["id"]
        return True
    return False


@st.dialog("Cambios sin guardar")
def _confirm_discard(direction: str):
    """Modal de confirmación al navegar con una evaluación editada sin guardar."""
    st.warning("Tenés una evaluación sin guardar en este ítem. Si continuás, se pierde.")
    d1, d2 = st.columns(2)
    with d1:
        if st.button("Cancelar", use_container_width=True, key="cap_discard_cancel"):
            st.session_state.pop("_cap_pending_nav", None)
            st.rerun()
    with d2:
        if st.button("Continuar sin guardar", type="primary", use_container_width=True, key="cap_discard_confirm"):
            st.session_state.pop("_cap_pending_nav", None)
            if direction == "next":
                _cap_advance()
            else:
                _cap_retreat()
            st.rerun()


@st.dialog("Reiniciar auditoría")
def _confirm_reset(local: str, fecha: str):
    """Modal de confirmación para borrar todas las evaluaciones de un local+mes."""
    st.warning(
        f"Esto borra **todas las evaluaciones guardadas** de **{local}** para este período "
        "(los ítems vuelven a quedar sin marcar). Las fotos ya cargadas NO se borran. "
        "**Esta acción no se puede deshacer.**"
    )
    r1, r2 = st.columns(2)
    with r1:
        if st.button("Cancelar", use_container_width=True, key="cap_reset_cancel"):
            st.session_state.pop("_cap_pending_reset", None)
            st.rerun()
    with r2:
        if st.button("Sí, borrar todo", type="primary", use_container_width=True, key="cap_reset_confirm"):
            db.delete_audit_results(local, fecha)
            db.delete_auditoria(local, fecha)
            db.clear_draft(st.session_state.get("rol", "operativo"))
            _get_eval_map.clear()
            st.session_state.pop("_cap_pending_reset", None)
            st.session_state.pop(f"_cap_celebrated_{local}_{fecha}", None)
            st.toast("🗑️ Auditoría reiniciada — todo sin evaluar de nuevo", icon="🗑️")
            st.rerun()


# ── Header ────────────────────────────────────────────────────────────────

st.markdown("## 📸 Captura y Evaluación")
st.caption("Sacá la foto y evaluá el ítem en el mismo paso, desde tu celular")

if use_mongo:
    st.success("🟢 Conectado a MongoDB Atlas — las fotos se guardan en la nube automáticamente")
else:
    st.warning(
        "⚠️ MongoDB no configurado. Las fotos se guardan solo en esta sesión. "
        "Configurá `MONGODB_URI` en Settings → Secrets para almacenamiento persistente."
    )

# ── Config (colapsada — casi nunca cambia dentro de una auditoría) ────────

_cfg_local_default = st.session_state.get("cap_local_name", LOCALES[0])
_cfg_date_default = st.session_state.get("cap_audit_date", date.today())
_cfg_tipo_default = st.session_state.get("cap_tipo_auditoria", TIPOS_AUDITORIA[0])
_cfg_date_str = (
    _cfg_date_default.strftime("%d/%m/%Y") if hasattr(_cfg_date_default, "strftime") else str(_cfg_date_default)
)
_cfg_summary = f"⚙️ {_cfg_local_default} · {_cfg_date_str} · {_cfg_tipo_default.replace('_', ' ').title()}"

with st.expander(_cfg_summary, expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        local_name = st.selectbox("🏪 Local", LOCALES, key="cap_local_name")
    with c2:
        audit_date = st.date_input("📅 Fecha", value=date.today(), key="cap_audit_date")
    with c3:
        tipo_auditoria = st.selectbox(
            "Tipo",
            TIPOS_AUDITORIA,
            format_func=lambda t: t.replace("_", " ").title(),
            key="cap_tipo_auditoria",
        )

    if use_mongo:
        st.divider()
        st.caption("⚠️ Zona de riesgo")
        if st.button(
            "🗑️ Reiniciar evaluaciones de este local/mes",
            use_container_width=True,
            key="cap_reset_btn",
            help="Borra todas las evaluaciones guardadas para volver a empezar de cero",
        ):
            st.session_state["_cap_pending_reset"] = True
            st.rerun()

fecha_str = audit_date.strftime("%Y-%m")
_eval_map = _get_eval_map(local_name, fecha_str)

if st.session_state.get("_cap_pending_reset"):
    _confirm_reset(local_name, fecha_str)

# ── Auditoría ya finalizada ──────────────────────────────────────────────
_auditoria_doc = db.get_auditoria(local_name, fecha_str) if use_mongo else None
_is_finalized = bool(_auditoria_doc and _auditoria_doc.get("finalizada"))
if _is_finalized:
    _fin_tipo = (_auditoria_doc or {}).get("tipo_auditoria", "—").replace("_", " ").title()
    st.warning(
        f"🔒 La auditoría de **{local_name}** para este período ya fue **finalizada** "
        f"({_fin_tipo}). Podés seguir evaluando si hace falta corregir algo, o usar "
        f"**🗑️ Reiniciar** (arriba en ⚙️) para empezar una auditoría nueva de cero."
    )

# ── Bienvenida (solo al llegar desde otra página) ───────────────────────
_should_resume = st.session_state.pop("_cap_should_resume", False)
if _should_resume:
    _rol_label = "Ivana" if st.session_state.get("rol", "operativo") == "operativo" else "Dirección"
    _next_pending_greet = next((c for c in CRITERIA if c["id"] not in _eval_map), None)
    if _next_pending_greet:
        st.info(
            f"👋 Hola, {_rol_label} — **{local_name}**: **{len(_eval_map)}/{len(CRITERIA)}** ítems evaluados. "
            f"Te llevamos directo a **{_next_pending_greet['id']} — {_next_pending_greet['name'][:45]}**."
        )
    else:
        st.success(f"🎉 ¡Auditoría completa en **{local_name}**! Evaluaste los {len(CRITERIA)} ítems.")

with st.sidebar:
    st.markdown("### 📖 Instrucciones")
    st.markdown(
        "1. Tocá **⚙️** arriba solo si necesitás cambiar local, fecha o tipo\n"
        "2. Sacá o subí la foto (opcional)\n"
        "3. Elegí a qué sección e ítem corresponde (o usá ← / →)\n"
        "4. Tocá Conforme / Observación / No Conforme y, si hace falta, una nota\n"
        "5. Tocá **✅ Guardar y siguiente** — guarda todo y pasa al próximo ítem\n"
        "6. Al terminar, revisá el reporte en 🔍 Auditoría"
    )
    st.divider()
    tp = _total_photos(local_name, fecha_str)
    if tp > 0:
        st.metric("Fotos totales", tp)
        st.caption(f"💾 Tamaño: {_total_size_str(local_name, fecha_str)}")

# ── Progreso ──────────────────────────────────────────────────────────────

total_items = len(CRITERIA)
items_covered = sum(1 for c in CRITERIA if c["id"] in _eval_map)

with st.container(border=True):
    st.markdown("### 📊 Progreso")
    st.progress(
        items_covered / total_items if total_items else 0,
        text=f"**{items_covered} / {total_items}** ítems evaluados",
    )

    metric_cols = st.columns(5)
    for i, (sec_key, short_name) in enumerate(SECTION_SHORT.items()):
        sec_items = get_criteria_by_section(sec_key)
        done = sum(1 for c in sec_items if c["id"] in _eval_map)
        with metric_cols[i]:
            st.metric(short_name, f"{done}/{len(sec_items)}")

# ── Captura ───────────────────────────────────────────────────────────────

# ── 1. Sacá la foto (primero, antes de elegir el ítem) ─────────────────────
if "_cap_photo_round" not in st.session_state:
    st.session_state["_cap_photo_round"] = 0
_round = st.session_state["_cap_photo_round"]

with st.container(border=True):
    st.markdown("### 📷 Sacá la foto")
    st.caption("Sacá o subí la foto primero; abajo elegís a qué ítem corresponde.")

    _cam_col, _gal_col = st.columns(2)
    with _cam_col:
        camera_photo = st.camera_input("Cámara", key=f"ccam_{_round}")
    with _gal_col:
        uploaded = st.file_uploader(
            "O subí desde galería",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key=f"cupload_{_round}",
        )

    if camera_photo or uploaded:
        st.success("📸 Foto lista. Elegí abajo a qué ítem corresponde y guardá.")

# ── 2. ¿A qué ítem corresponde? ─────────────────────────────────────────────
with st.container(border=True):
    st.markdown("### 🏷️ ¿A qué ítem corresponde?")

    # Navegación pendiente (ver botones ← / → más abajo) — debe aplicarse ANTES
    # de instanciar los selectbox de sección/ítem.
    _nav_sec = st.session_state.pop("_cap_nav_section", None)
    _nav_item_id = st.session_state.pop("_cap_nav_item", None)

    # Al entrar a esta página desde otra (barra inferior), saltar directo al
    # próximo ítem sin evaluar en vez de quedarse en uno ya evaluado.
    # (_should_resume ya se consumió arriba, para el mensaje de bienvenida.)
    if _should_resume and _nav_sec is None:
        _next_pending = next((c for c in CRITERIA if c["id"] not in _eval_map), None)
        if _next_pending:
            _nav_sec = _next_pending["section"]
            _nav_item_id = _next_pending["id"]

    if _nav_sec is not None:
        st.session_state.pop("cap_section", None)
        st.session_state.pop("cap_item", None)

    _section_keys = list(SECTIONS.keys())
    if _nav_sec in _section_keys:
        _sec_default = _section_keys.index(_nav_sec)
    elif st.session_state.get("cap_section") in _section_keys:
        # No hay navegación pendiente: mantener la sección donde estaba, en vez
        # de volver siempre a la primera (A).
        _sec_default = _section_keys.index(st.session_state["cap_section"])
    else:
        _sec_default = 0
    section = st.selectbox(
        "Sección",
        _section_keys,
        index=_sec_default,
        format_func=lambda x: f"{x}. {SECTION_SHORT[x]}",
        key="cap_section",
    )

    section_items = get_criteria_by_section(section)

    def _item_label(item: dict) -> str:
        iid = item["id"]
        name = item["name"]
        if len(name) > 45:
            name = name[:42] + "..."
        ev = _eval_map.get(iid)
        if ev:
            icon = STATUS_ICONS.get(ev.get("status", ""), "✅")
        elif iid in NO_PHOTO_ITEMS:
            icon = "⏭️"
        else:
            icon = "⬜"
        return f"{icon} {iid} — {name}"

    _item_ids = [c["id"] for c in section_items]
    _prev_selected_item = st.session_state.get("cap_item")
    if _nav_item_id in _item_ids:
        _item_default = _item_ids.index(_nav_item_id)
    elif isinstance(_prev_selected_item, dict) and _prev_selected_item.get("id") in _item_ids:
        _item_default = _item_ids.index(_prev_selected_item["id"])
    else:
        _item_default = 0
    selected = st.selectbox(
        "Ítem", section_items, index=_item_default, format_func=_item_label, key="cap_item"
    )

    _all_ids = [c["id"] for c in CRITERIA]
    _cur_idx = _all_ids.index(selected["id"]) if selected and selected["id"] in _all_ids else 0
    st.caption(f"Ítem {_cur_idx + 1} de {len(_all_ids)} (recorrido completo)")

    # ¿Hay una evaluación editada en pantalla que todavía no se guardó?
    _saved_for_cur = _eval_map.get(selected["id"]) if selected else None
    _cur_status_val = st.session_state.get(f"cap_eval_status_{selected['id']}") if selected else None
    _cur_nota_val = st.session_state.get(f"cap_eval_nota_{selected['id']}", "") if selected else ""
    _has_unsaved = False
    if _cur_status_val is not None:
        _saved_status_val = _saved_for_cur.get("status", "Conforme") if _saved_for_cur else "Conforme"
        _saved_nota_val = _saved_for_cur.get("justificacion", "") if _saved_for_cur else ""
        _has_unsaved = (_cur_status_val != _saved_status_val) or (_cur_nota_val.strip() != _saved_nota_val.strip())

    _nav_c1, _nav_c2 = st.columns(2)
    with _nav_c1:
        if st.button("← Ítem anterior", use_container_width=True, disabled=_cur_idx == 0, key="cap_btn_prev"):
            if _has_unsaved:
                st.session_state["_cap_pending_nav"] = "prev"
                st.rerun()
            elif _cap_retreat():
                st.rerun()
    with _nav_c2:
        if st.button(
            "Ítem siguiente →",
            use_container_width=True,
            disabled=_cur_idx == len(_all_ids) - 1,
            key="cap_btn_next",
            type="primary",
        ):
            if _has_unsaved:
                st.session_state["_cap_pending_nav"] = "next"
                st.rerun()
            elif _cap_advance():
                st.rerun()

    _pending_nav = st.session_state.get("_cap_pending_nav")
    if _pending_nav:
        _confirm_discard(_pending_nav)

if selected:
    item_id = selected["id"]

    with st.container(border=True):
        with st.expander("ℹ️ Qué evalúa este ítem", expanded=False):
            st.markdown(f"**{selected['name']}**")
            if selected.get("conforme"):
                st.markdown(f"✅ **Conforme:** {selected['conforme']}")
            if selected.get("observacion"):
                st.markdown(f"⚠️ **Observación:** {selected['observacion']}")
            if selected.get("no_conforme"):
                st.markdown(f"❌ **No conforme:** {selected['no_conforme']}")

        if item_id in NO_PHOTO_ITEMS:
            st.caption("ℹ️ Ítem oral/presencial — no requiere foto.")

        # ── Fotos ya cargadas para este ítem (evidencia previa) ────────────
        if item_id not in NO_PHOTO_ITEMS:
            if use_mongo:
                item_photos = db.get_photos_for_item(local_name, fecha_str, item_id)
            else:
                item_photos_raw = st.session_state.cap_photos.get(item_id, [])
                item_photos = [
                    {"_id": str(i), "photo_data": p["data"], "photo_name": p["name"]}
                    for i, p in enumerate(item_photos_raw)
                ]

            _n_photos = len(item_photos)
            if _n_photos:
                _preview_n = min(_n_photos, 5)
                _preview_cols = st.columns(_preview_n + (1 if _n_photos > 5 else 0))
                for i in range(_preview_n):
                    with _preview_cols[i]:
                        st.image(item_photos[i]["photo_data"], width=48)
                if _n_photos > 5:
                    with _preview_cols[5]:
                        st.caption(f"+{_n_photos - 5}")

                with st.expander(f"📸 Fotos ya cargadas para este ítem ({_n_photos})", expanded=False):
                    for row_start in range(0, len(item_photos), 3):
                        cols = st.columns(3)
                        for j in range(3):
                            idx = row_start + j
                            if idx >= len(item_photos):
                                break
                            photo = item_photos[idx]
                            with cols[j]:
                                st.image(
                                    photo["photo_data"],
                                    caption=photo["photo_name"],
                                    use_container_width=True,
                                )
                                _del_confirm_key = f"_cap_confirm_del_{item_id}_{idx}"
                                if st.session_state.get(_del_confirm_key):
                                    st.warning("¿Borrar esta foto?")
                                    dcol1, dcol2 = st.columns(2)
                                    with dcol1:
                                        if st.button(
                                            "Sí, borrar",
                                            key=f"cdel_yes_{item_id}_{idx}",
                                            type="primary",
                                            use_container_width=True,
                                        ):
                                            if use_mongo:
                                                db.delete_photo(str(photo["_id"]))
                                                _get_counts.clear()
                                            else:
                                                st.session_state.cap_photos[item_id].pop(idx)
                                                if not st.session_state.cap_photos[item_id]:
                                                    del st.session_state.cap_photos[item_id]
                                            st.session_state.pop(_del_confirm_key, None)
                                            st.toast("🗑️ Foto borrada")
                                            st.rerun()
                                    with dcol2:
                                        if st.button(
                                            "Cancelar",
                                            key=f"cdel_no_{item_id}_{idx}",
                                            use_container_width=True,
                                        ):
                                            st.session_state.pop(_del_confirm_key, None)
                                            st.rerun()
                                else:
                                    if st.button(
                                        "🗑️ Borrar",
                                        key=f"cdel_{item_id}_{idx}",
                                        help="Borrar esta foto",
                                        use_container_width=True,
                                    ):
                                        st.session_state[_del_confirm_key] = True
                                        st.rerun()

        # ── 3. Evaluación ────────────────────────────────────────────────────
        st.divider()
        st.markdown("### ✍️ Evaluación")

        _prev_eval = _eval_map.get(item_id)
        _status_key = f"cap_eval_status_{item_id}"
        if _status_key not in st.session_state:
            st.session_state[_status_key] = _prev_eval.get("status", "Conforme") if _prev_eval else "Conforme"
        eval_status = st.session_state[_status_key]

        if not use_mongo:
            st.warning("MongoDB no configurado — la evaluación no se puede guardar sin persistencia.")

        def _sel(status: str) -> str:
            return "sel" if status == eval_status else "unsel"

        bcol1, bcol2, bcol3 = st.columns(3)
        with bcol1:
            if st.button(
                "✅ Conforme", use_container_width=True, key=f"cap_btn_conforme_{item_id}_{_sel('Conforme')}"
            ):
                st.session_state[_status_key] = "Conforme"
                st.rerun()
        with bcol2:
            if st.button(
                "⚠️ Observación", use_container_width=True, key=f"cap_btn_observacion_{item_id}_{_sel('Observación')}"
            ):
                st.session_state[_status_key] = "Observación"
                st.rerun()
        with bcol3:
            if st.button(
                "❌ No conforme", use_container_width=True, key=f"cap_btn_noconforme_{item_id}_{_sel('No Conforme')}"
            ):
                st.session_state[_status_key] = "No Conforme"
                st.rerun()

        _nota_needed = eval_status != "Conforme"
        _nota_default = _prev_eval.get("justificacion", "") if _prev_eval else ""
        eval_nota = st.text_area(
            "Nota — qué se observó" + (" (obligatoria)" if _nota_needed else " (opcional)"),
            value=_nota_default,
            key=f"cap_eval_nota_{item_id}",
            placeholder="Ej: Exhibidora fuera de lugar, falta cartel de precios...",
        )
        _nota_ok = (not _nota_needed) or bool(eval_nota.strip())
        if _nota_needed and not _nota_ok:
            st.warning("Agregá una nota breve antes de guardar.")

        if _prev_eval:
            st.caption(
                f"Última evaluación guardada: {STATUS_ICONS.get(_prev_eval.get('status',''), '')} "
                f"{_prev_eval.get('status','')} — {_prev_eval.get('analyzed_at','')}"
            )

        # ── 4. Guardar (único botón) ────────────────────────────────────────
        st.divider()
        if st.button(
            "✅ Guardar y siguiente",
            type="primary",
            use_container_width=True,
            disabled=not _nota_ok or not use_mongo,
            key=f"cap_save_{item_id}",
        ):
            ok = _persist_evaluation(local_name, fecha_str, section, selected, eval_status, eval_nota, tipo_auditoria)
            saved_photo = False
            try:
                if camera_photo is not None:
                    compressed = compress_photo(camera_photo)
                    if use_mongo:
                        name = db.next_photo_name(local_name, fecha_str, item_id)
                        db.save_photo(local_name, fecha_str, section, item_id, compressed, name)
                        _get_counts.clear()
                    else:
                        code = item_id.replace(".", "")
                        st.session_state.cap_photos.setdefault(item_id, [])
                        n = len(st.session_state.cap_photos[item_id]) + 1
                        st.session_state.cap_photos[item_id].append(
                            {"data": compressed, "name": f"{code}_{n:03d}.jpg"}
                        )
                    saved_photo = True
                if uploaded:
                    for f in uploaded:
                        compressed = compress_photo(f)
                        if use_mongo:
                            name = db.next_photo_name(local_name, fecha_str, item_id)
                            db.save_photo(local_name, fecha_str, section, item_id, compressed, name)
                        else:
                            code = item_id.replace(".", "")
                            st.session_state.cap_photos.setdefault(item_id, [])
                            n = len(st.session_state.cap_photos[item_id]) + 1
                            st.session_state.cap_photos[item_id].append(
                                {"data": compressed, "name": f"{code}_{n:03d}.jpg"}
                            )
                    if use_mongo:
                        _get_counts.clear()
                    saved_photo = True
            except Exception as e:
                st.error(f"No se pudo guardar la foto: {e}")

            if ok:
                st.toast(
                    "✅ Evaluación guardada" + (" con foto" if saved_photo else ""),
                    icon="✅",
                )
                if saved_photo:
                    st.session_state["_cap_photo_round"] += 1
                _cap_advance()
                st.rerun()

        # ── 5. Finalizar auditoría (disponible en cualquier momento) ────────
        st.caption(
            "¿Ya terminaste? Podés cerrar la auditoría cuando quieras: queda "
            "**completa** si evaluaste los 61 ítems, o **parcial** si faltan algunos."
        )
        if st.button(
            "🏁 Finalizar auditoría",
            use_container_width=True,
            disabled=not use_mongo or items_covered == 0,
            key="cap_finalize_btn",
        ):
            _final_tipo = "completa" if items_covered >= total_items else "parcial"
            db.upsert_auditoria(
                local=local_name,
                fecha=fecha_str,
                tipo=_final_tipo,
                created_by=st.session_state.get("rol", "operativo"),
                finalizada=True,
            )
            # El borrador local de la página Revisar (si existiera) queda
            # huérfano apenas se finaliza desde acá.
            db.clear_draft(st.session_state.get("rol", "operativo"))
            if _final_tipo == "completa":
                st.toast(
                    f"🏁 Auditoría COMPLETA finalizada — {items_covered}/{total_items} ítems", icon="🏁"
                )
            else:
                st.toast(
                    f"🏁 Auditoría PARCIAL finalizada — {items_covered}/{total_items} ítems", icon="🏁"
                )
            st.rerun()

# ── Finalizar ─────────────────────────────────────────────────────────────

tp = _total_photos(local_name, fecha_str)
missing = [c for c in CRITERIA if c["id"] not in _eval_map]

with st.container(border=True):
    st.markdown("### ✅ Finalizar")

    if items_covered >= total_items and total_items > 0:
        # ── Pantalla de cierre ──────────────────────────────────────────────
        _status_counts = {"Conforme": 0, "Observación": 0, "No Conforme": 0}
        for r in _eval_map.values():
            s = r.get("status", "Conforme")
            if s in _status_counts:
                _status_counts[s] += 1
        _pct_conforme = round(_status_counts["Conforme"] / total_items * 100) if total_items else 0
        _n_desvios = _status_counts["Observación"] + _status_counts["No Conforme"]

        _celebrate_key = f"_cap_celebrated_{local_name}_{fecha_str}"
        if not st.session_state.get(_celebrate_key):
            st.balloons()
            st.session_state[_celebrate_key] = True

        st.success(f"🎉 ¡Auditoría completa en **{local_name}**! Evaluaste los {total_items} ítems.")
        ccol1, ccol2, ccol3 = st.columns(3)
        ccol1.metric("✅ Conforme", _status_counts["Conforme"])
        ccol2.metric("⚠️ Observación", _status_counts["Observación"])
        ccol3.metric("❌ No Conforme", _status_counts["No Conforme"])
        st.caption(
            f"**{_pct_conforme}%** de conformidad global · **{tp}** fotos cargadas · "
            f"Los **{_n_desvios}** desvíos detectados quedaron cargados en 📊 Planes de Mejora."
        )

    elif items_covered > 0:
        st.markdown(
            f"**{items_covered} de {total_items}** ítems evaluados "
            f"({tp} fotos, {_total_size_str(local_name, fecha_str)})"
        )
        if missing:
            with st.expander(f"ℹ️ {len(missing)} ítems sin evaluar"):
                for sec_key in SECTIONS:
                    sec_missing = [m for m in missing if m["section"] == sec_key]
                    if sec_missing:
                        st.markdown(
                            f"**{sec_key}. {SECTION_SHORT[sec_key]}** ({len(sec_missing)})"
                        )
                        for m in sec_missing:
                            st.markdown(f"- {m['id']} — {m['name'][:55]}...")

        if use_mongo:
            st.success(
                "✅ La evaluación se guarda en la nube a medida que avanzás. "
                "Podés cerrar el navegador tranquilo."
            )
        else:
            local_slug = (local_name.strip().replace(" ", "-") or "Local")
            zip_data = _build_zip(local_name, fecha_str)
            st.download_button(
                "📥 Descargar ZIP (fotos)",
                data=zip_data,
                file_name=f"auditoria_{fecha_str}_{local_slug}.zip",
                mime="application/zip",
                use_container_width=True,
                type="primary",
            )
            st.info("💡 Descargá el ZIP antes de cerrar — sin MongoDB las fotos no persisten.")
    else:
        st.caption("Empezá a evaluar ítems para poder finalizar.")

# ── Footer ────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    "📸 Grido Fotos — Captura y evaluación en un solo paso. Las fotos se comprimen "
    "automáticamente (~90% de ahorro). "
    + ("Almacenadas en MongoDB Atlas." if use_mongo else "Almacenadas en la sesión.")
)
