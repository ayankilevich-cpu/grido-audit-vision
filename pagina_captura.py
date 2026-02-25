"""
Grido Fotos — Captura de fotos para auditoría.
Guarda fotos comprimidas en MongoDB Atlas (o session_state como fallback).
"""

from __future__ import annotations

import io
import zipfile
from datetime import date, datetime

import streamlit as st
from PIL import Image

from criteria import CRITERIA, SECTIONS, get_criteria_by_section
import db

# ── Constantes ────────────────────────────────────────────────────────────

MAX_DIM = 1200
JPEG_QUALITY = 80

NO_PHOTO_ITEMS = {"C.17"}

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
.stButton>button {min-height:44px;}
div[data-testid="stMetric"] {
    background:#f8f9fa; border-radius:8px; padding:.5rem;
    text-align:center; box-shadow:0 1px 3px rgba(0,0,0,.08);
}
div[data-testid="stMetric"] label {font-size:.75rem !important;}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {font-size:1.1rem !important;}
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


# ── Header ────────────────────────────────────────────────────────────────

st.markdown("## 📸 Captura de Fotos")
st.caption("Sacá las fotos de auditoría desde tu celular")

if use_mongo:
    st.success("🟢 Conectado a MongoDB Atlas — las fotos se guardan en la nube automáticamente")
else:
    st.warning(
        "⚠️ MongoDB no configurado. Las fotos se guardan solo en esta sesión. "
        "Configurá `MONGODB_URI` en Settings → Secrets para almacenamiento persistente."
    )

# ── Config ────────────────────────────────────────────────────────────────

c1, c2 = st.columns(2)
with c1:
    local_name = st.text_input(
        "🏪 Local", placeholder="Nombre del local", key="cap_local_name"
    )
with c2:
    audit_date = st.date_input("📅 Fecha", value=date.today(), key="cap_audit_date")

fecha_str = audit_date.strftime("%Y-%m")

with st.sidebar:
    st.markdown("### 📖 Instrucciones")
    st.markdown(
        "1. Escribí el nombre del local\n"
        "2. Elegí la sección y el ítem\n"
        "3. Sacá fotos o subí desde galería\n"
        "4. Tocá **Guardar**\n"
        "5. Pasá al siguiente ítem\n"
        "6. Al terminar, descargá el ZIP"
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
st.markdown("### 📷 Capturar fotos")

section = st.selectbox(
    "Sección",
    list(SECTIONS.keys()),
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


selected = st.selectbox("Ítem", section_items, format_func=_item_label, key="cap_item")

if selected:
    item_id = selected["id"]

    if item_id in NO_PHOTO_ITEMS:
        st.info("ℹ️ Este ítem se evalúa de forma oral/presencial y no requiere fotos.")
    else:
        with st.expander("ℹ️ Qué evalúa este ítem", expanded=False):
            st.markdown(f"**{selected['name']}**")
            if selected.get("conforme"):
                st.markdown(f"✅ **Conforme:** {selected['conforme']}")
            if selected.get("observacion"):
                st.markdown(f"⚠️ **Observación:** {selected['observacion']}")
            if selected.get("no_conforme"):
                st.markdown(f"❌ **No conforme:** {selected['no_conforme']}")

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
        tab_gallery, tab_camera = st.tabs(["📁 Galería / Archivo", "📷 Cámara"])

        with tab_gallery:
            uploaded = st.file_uploader(
                "Elegí fotos",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
                key=f"cupload_{item_id}",
                label_visibility="collapsed",
            )
            if uploaded:
                if st.button(
                    f"💾 Guardar {len(uploaded)} foto(s)",
                    key=f"csave_gal_{item_id}",
                    type="primary",
                    use_container_width=True,
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
                        st.success(f"✅ {saved} foto(s) guardadas para {item_id}")
                        st.rerun()

        with tab_camera:
            camera_photo = st.camera_input(
                "Sacá una foto",
                key=f"ccam_{item_id}",
                label_visibility="collapsed",
            )
            if camera_photo:
                if st.button(
                    "💾 Guardar foto",
                    key=f"csave_cam_{item_id}",
                    type="primary",
                    use_container_width=True,
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
                        st.success(f"✅ Foto guardada para {item_id}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

# ── Finalizar ─────────────────────────────────────────────────────────────

st.divider()
st.markdown("### ✅ Finalizar")

missing = [
    c
    for c in CRITERIA
    if _photo_count(local_name, fecha_str, c["id"]) == 0
    and c["id"] not in NO_PHOTO_ITEMS
]

if missing:
    st.warning(f"⚠️ Faltan fotos de **{len(missing)}** ítems.")
    with st.expander("Ver ítems pendientes"):
        for sec_key in SECTIONS:
            sec_missing = [m for m in missing if m["section"] == sec_key]
            if sec_missing:
                st.markdown(
                    f"**{sec_key}. {SECTION_SHORT[sec_key]}** ({len(sec_missing)} pendientes)"
                )
                for m in sec_missing:
                    st.markdown(f"- {m['id']} — {m['name'][:55]}...")
else:
    st.success("🎉 ¡Todos los ítems tienen fotos!")

has_photos = _total_photos(local_name, fecha_str) > 0

if has_photos:
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

# ── Footer ────────────────────────────────────────────────────────────────

st.divider()
st.caption(
    "📸 Grido Fotos — Las fotos se comprimen automáticamente (~90% de ahorro). "
    + ("Almacenadas en MongoDB Atlas." if use_mongo else "Almacenadas en la sesión.")
)
