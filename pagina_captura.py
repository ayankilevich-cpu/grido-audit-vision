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
/* Touch targets — mínimo 44px para tablet */
.stButton>button {
    min-height: 48px !important;
    font-size: 1rem !important;
}
div[data-testid="stSelectbox"] > div > div {
    min-height: 48px !important;
    font-size: 1rem !important;
}
.stTabs [data-baseweb="tab"] {
    min-height: 48px !important;
    font-size: 0.95rem !important;
    padding: 0 20px !important;
}
div[data-testid="stFileUploader"] label {
    min-height: 48px !important;
}
div[data-testid="stExpander"] summary {
    min-height: 48px !important;
    font-size: 0.95rem !important;
}
/* Métricas de progreso */
div[data-testid="stMetric"] {
    background: #f8f9fa;
    border-radius: 8px;
    padding: .5rem;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,.08);
}
div[data-testid="stMetric"] label { font-size: .75rem !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.1rem !important; }
/* Más espaciado entre elementos en tablet */
.block-container { padding-top: 1.5rem !important; }
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

# ── Config ────────────────────────────────────────────────────────────────

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

fecha_str = audit_date.strftime("%Y-%m")

with st.sidebar:
    st.markdown("### 📖 Instrucciones")
    st.markdown(
        "1. Elegí local, fecha y tipo de auditoría\n"
        "2. Elegí la sección y el ítem (o usá ← / →)\n"
        "3. Marcá Conforme / Observación / No Conforme y, si hace falta, una nota\n"
        "4. Sacá o subí la foto y tocá **Guardar foto + evaluación** "
        "(o **Guardar evaluación y pasar al siguiente ítem** si no hay foto)\n"
        "5. Al terminar, revisá el reporte en 🔍 Auditoría"
    )
    st.divider()
    tp = _total_photos(local_name, fecha_str)
    if tp > 0:
        st.metric("Fotos totales", tp)
        st.caption(f"💾 Tamaño: {_total_size_str(local_name, fecha_str)}")

# ── Progreso ──────────────────────────────────────────────────────────────

st.divider()
st.markdown("### 📊 Progreso")

total_items = len(CRITERIA)
items_covered = sum(
    1
    for c in CRITERIA
    if _photo_count(local_name, fecha_str, c["id"]) > 0 or c["id"] in NO_PHOTO_ITEMS
)

st.progress(
    items_covered / total_items if total_items else 0,
    text=f"**{items_covered} / {total_items}** ítems con fotos",
)

metric_cols = st.columns(5)
for i, (sec_key, short_name) in enumerate(SECTION_SHORT.items()):
    sec_items = get_criteria_by_section(sec_key)
    done = sum(
        1
        for c in sec_items
        if _photo_count(local_name, fecha_str, c["id"]) > 0 or c["id"] in NO_PHOTO_ITEMS
    )
    with metric_cols[i]:
        st.metric(short_name, f"{done}/{len(sec_items)}")

# ── Captura ───────────────────────────────────────────────────────────────

st.divider()
st.markdown("### 📷 Capturar y evaluar")

# Navegación pendiente (ver botones ← / → más abajo) — debe aplicarse ANTES
# de instanciar los selectbox de sección/ítem.
_nav_sec = st.session_state.pop("_cap_nav_section", None)
_nav_item_id = st.session_state.pop("_cap_nav_item", None)
if _nav_sec is not None:
    st.session_state.pop("cap_section", None)
    st.session_state.pop("cap_item", None)

_section_keys = list(SECTIONS.keys())
_sec_default = _section_keys.index(_nav_sec) if _nav_sec in _section_keys else 0
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
    n = _photo_count(local_name, fecha_str, iid)
    if iid in NO_PHOTO_ITEMS:
        return f"⏭️ {iid} — {name} (oral)"
    if n > 0:
        return f"✅ {iid} — {name} ({n})"
    return f"⬜ {iid} — {name}"


_item_ids = [c["id"] for c in section_items]
_item_default = _item_ids.index(_nav_item_id) if _nav_item_id in _item_ids else 0
selected = st.selectbox(
    "Ítem", section_items, index=_item_default, format_func=_item_label, key="cap_item"
)

_all_ids = [c["id"] for c in CRITERIA]
_cur_idx = _all_ids.index(selected["id"]) if selected and selected["id"] in _all_ids else 0
st.caption(f"Ítem {_cur_idx + 1} de {len(_all_ids)} (recorrido completo)")
_nav_c1, _nav_c2 = st.columns(2)
with _nav_c1:
    if st.button("← Ítem anterior", use_container_width=True, disabled=_cur_idx == 0, key="cap_btn_prev"):
        if _cap_retreat():
            st.rerun()
with _nav_c2:
    if st.button(
        "Ítem siguiente →",
        use_container_width=True,
        disabled=_cur_idx == len(_all_ids) - 1,
        key="cap_btn_next",
        type="primary",
    ):
        if _cap_advance():
            st.rerun()

if selected:
    item_id = selected["id"]

    with st.expander("ℹ️ Qué evalúa este ítem", expanded=False):
        st.markdown(f"**{selected['name']}**")
        if selected.get("conforme"):
            st.markdown(f"✅ **Conforme:** {selected['conforme']}")
        if selected.get("observacion"):
            st.markdown(f"⚠️ **Observación:** {selected['observacion']}")
        if selected.get("no_conforme"):
            st.markdown(f"❌ **No conforme:** {selected['no_conforme']}")

    if item_id in NO_PHOTO_ITEMS:
        st.info("ℹ️ Este ítem se evalúa de forma oral/presencial y no requiere fotos.")

    # ── Evaluación ───────────────────────────────────────────────────
    st.markdown("### ✍️ Evaluación")

    _eval_map = _get_eval_map(local_name, fecha_str)
    _prev_eval = _eval_map.get(item_id)
    _status_default_idx = (
        STATUSES.index(_prev_eval["status"]) if _prev_eval and _prev_eval.get("status") in STATUSES else 0
    )
    _nota_default = _prev_eval.get("justificacion", "") if _prev_eval else ""

    if not use_mongo:
        st.warning("MongoDB no configurado — la evaluación no se puede guardar sin persistencia.")

    eval_status = st.radio(
        "Estado del ítem",
        STATUSES,
        index=_status_default_idx,
        horizontal=True,
        key=f"cap_eval_status_{item_id}",
    )
    _nota_needed = eval_status != "Conforme"
    eval_nota = st.text_area(
        "Nota — qué se observó" + (" (obligatoria)" if _nota_needed else " (opcional)"),
        value=_nota_default,
        key=f"cap_eval_nota_{item_id}",
        placeholder="Ej: Exhibidora fuera de lugar, falta cartel de precios...",
    )
    _nota_ok = (not _nota_needed) or bool(eval_nota.strip())
    if _nota_needed and not _nota_ok:
        st.warning("Agregá una nota breve antes de guardar la evaluación.")

    if _prev_eval:
        st.caption(
            f"Última evaluación guardada: {STATUS_ICONS.get(_prev_eval.get('status',''), '')} "
            f"{_prev_eval.get('status','')} — {_prev_eval.get('analyzed_at','')}"
        )

    if st.button(
        "💾 Guardar evaluación y pasar al siguiente ítem",
        type="primary",
        use_container_width=True,
        disabled=not _nota_ok or not use_mongo,
        key=f"cap_save_eval_{item_id}",
    ):
        if _persist_evaluation(local_name, fecha_str, section, selected, eval_status, eval_nota, tipo_auditoria):
            st.success(f"✅ Evaluación guardada para {item_id}")
            if _cap_advance():
                st.rerun()

    if item_id not in NO_PHOTO_ITEMS:
        # ── Fotos existentes ──────────────────────────────────────────

        if use_mongo:
            item_photos = db.get_photos_for_item(local_name, fecha_str, item_id)
        else:
            item_photos_raw = st.session_state.cap_photos.get(item_id, [])
            item_photos = [
                {"_id": str(i), "photo_data": p["data"], "photo_name": p["name"]}
                for i, p in enumerate(item_photos_raw)
            ]

        if item_photos:
            st.markdown(f"**📸 Fotos guardadas: {len(item_photos)}**")
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
                        if st.button(
                            "🗑️",
                            key=f"cdel_{item_id}_{idx}",
                            help="Borrar esta foto",
                        ):
                            if use_mongo:
                                db.delete_photo(str(photo["_id"]))
                                _get_counts.clear()
                            else:
                                st.session_state.cap_photos[item_id].pop(idx)
                                if not st.session_state.cap_photos[item_id]:
                                    del st.session_state.cap_photos[item_id]
                            st.rerun()

        # ── Agregar fotos ─────────────────────────────────────────────

        st.markdown("**Agregar fotos:**")
        tab_camera, tab_gallery = st.tabs(["📷 Cámara", "📁 Galería / Archivo"])

        with tab_camera:
            camera_photo = st.camera_input(
                "Sacá una foto",
                key=f"ccam_{item_id}",
                label_visibility="collapsed",
            )

            if camera_photo:
                st.caption("Al guardar la foto también se guarda la evaluación de arriba.")
                if st.button(
                    "💾 Guardar foto + evaluación",
                    key=f"csave_cam_{item_id}",
                    type="primary",
                    use_container_width=True,
                    disabled=not _nota_ok,
                ):
                    try:
                        compressed = compress_photo(camera_photo)
                        if use_mongo:
                            name = db.next_photo_name(local_name, fecha_str, item_id)
                            db.save_photo(
                                local_name, fecha_str, section, item_id,
                                compressed, name,
                            )
                            _get_counts.clear()
                        else:
                            code = item_id.replace(".", "")
                            if item_id not in st.session_state.cap_photos:
                                st.session_state.cap_photos[item_id] = []
                            n = len(st.session_state.cap_photos[item_id]) + 1
                            st.session_state.cap_photos[item_id].append(
                                {"data": compressed, "name": f"{code}_{n:03d}.jpg"}
                            )
                        _persist_evaluation(
                            local_name, fecha_str, section, selected, eval_status, eval_nota, tipo_auditoria
                        )
                        st.success(f"✅ Foto y evaluación guardadas para {item_id}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

        with tab_gallery:
            uploaded = st.file_uploader(
                "Elegí fotos",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
                key=f"cupload_{item_id}",
                label_visibility="collapsed",
            )
            if uploaded:
                st.caption("Al guardar las fotos también se guarda la evaluación de arriba.")
                if st.button(
                    f"💾 Guardar {len(uploaded)} foto(s) + evaluación",
                    key=f"csave_gal_{item_id}",
                    type="primary",
                    use_container_width=True,
                    disabled=not _nota_ok,
                ):
                    saved = 0
                    for f in uploaded:
                        try:
                            compressed = compress_photo(f)
                            if use_mongo:
                                name = db.next_photo_name(local_name, fecha_str, item_id)
                                db.save_photo(
                                    local_name, fecha_str, section, item_id,
                                    compressed, name,
                                )
                            else:
                                code = item_id.replace(".", "")
                                if item_id not in st.session_state.cap_photos:
                                    st.session_state.cap_photos[item_id] = []
                                n = len(st.session_state.cap_photos[item_id]) + 1
                                st.session_state.cap_photos[item_id].append(
                                    {"data": compressed, "name": f"{code}_{n:03d}.jpg"}
                                )
                            saved += 1
                        except Exception as e:
                            st.error(f"Error con {f.name}: {e}")

                    if saved:
                        if use_mongo:
                            _get_counts.clear()
                        _persist_evaluation(
                            local_name, fecha_str, section, selected, eval_status, eval_nota, tipo_auditoria
                        )
                        st.success(f"✅ {saved} foto(s) y evaluación guardadas para {item_id}")
                        st.rerun()

# ── Finalizar ─────────────────────────────────────────────────────────────

st.divider()
st.markdown("### ✅ Finalizar")

has_photos = _total_photos(local_name, fecha_str) > 0
tp = _total_photos(local_name, fecha_str)

missing = [
    c
    for c in CRITERIA
    if _photo_count(local_name, fecha_str, c["id"]) == 0
    and c["id"] not in NO_PHOTO_ITEMS
]

if has_photos:
    st.markdown(
        f"**{items_covered} de {total_items}** ítems cubiertos "
        f"({tp} fotos, {_total_size_str(local_name, fecha_str)})"
    )
    if missing:
        with st.expander(f"ℹ️ {len(missing)} ítems sin fotos (opcional)"):
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
            "✅ Las fotos ya están guardadas en la nube. "
            "Podés cerrar el navegador tranquilo."
        )
    else:
        local_slug = (local_name.strip().replace(" ", "-") or "Local")
        zip_data = _build_zip(local_name, fecha_str)
        st.download_button(
            "📥 Descargar ZIP",
            data=zip_data,
            file_name=f"auditoria_{fecha_str}_{local_slug}.zip",
            mime="application/zip",
            use_container_width=True,
            type="primary",
        )
        st.info("💡 Descargá el ZIP antes de cerrar — sin MongoDB las fotos no persisten.")
else:
    st.caption("Empezá a sacar fotos para poder finalizar.")

# ── Footer ────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    "📸 Grido Fotos — Captura y evaluación en un solo paso. Las fotos se comprimen "
    "automáticamente (~90% de ahorro). "
    + ("Almacenadas en MongoDB Atlas." if use_mongo else "Almacenadas en la sesión.")
)
