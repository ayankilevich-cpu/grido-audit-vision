"""
Grido Audit Vision — Página de auditoría.
Revisá las fotos de tu heladería y evaluá manualmente el cumplimiento de los
criterios de la Guía de Auditoría Operativa Grido. Incluye una sugerencia de
IA opcional (beta), pero la evaluación final siempre la define el auditor.
"""

from __future__ import annotations

import base64
import io
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from openai import OpenAI

from criteria import (
    CRITERIA,
    LOCALES,
    SECTIONS,
    TIPOS_AUDITORIA,
    get_criteria_by_section,
    get_criterion_by_id,
    get_section_name,
)
import db

# ── CSS tablet ──────────────────────────────────────────────────────────
_TABLET_CSS = """
<style>
/* Touch targets generales */
.stButton > button {
    min-height: 50px !important;
    font-size: 1rem !important;
}
div[data-testid="stSelectbox"] > div > div {
    min-height: 50px !important;
    font-size: 1rem !important;
}
.stTabs [data-baseweb="tab"] {
    min-height: 48px !important;
    padding: 0 18px !important;
    font-size: 0.9rem !important;
}
/* File uploader más grande */
div[data-testid="stFileUploader"] section {
    min-height: 80px !important;
}
div[data-testid="stFileUploader"] label {
    font-size: 1rem !important;
}
/* Expanders */
div[data-testid="stExpander"] summary {
    min-height: 48px !important;
    font-size: 0.95rem !important;
}
/* Espaciado del contenedor */
.block-container { padding-top: 1.5rem !important; }

/* Tarjetas grandes de estado — mismo lenguaje visual que 📸 Captura */
div[class*="st-key-aud_btn_conforme_"] button {
    background: #2ecc71 !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
    min-height: 58px !important;
    border-radius: 10px !important;
}
div[class*="st-key-aud_btn_observacion_"] button {
    background: #f39c12 !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
    min-height: 58px !important;
    border-radius: 10px !important;
}
div[class*="st-key-aud_btn_noconforme_"] button {
    background: #e74c3c !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
    min-height: 58px !important;
    border-radius: 10px !important;
}
div[class*="_unsel"] button {
    opacity: 0.42 !important;
}
div[class*="_sel"] button {
    opacity: 1 !important;
    box-shadow: 0 0 0 3px rgba(0,0,0,0.35) inset !important;
}
</style>
"""
st.markdown(_TABLET_CSS, unsafe_allow_html=True)

TOTAL_ITEMS = len(CRITERIA)
DRAFT_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / ".audit_drafts"
DRAFT_DIR.mkdir(exist_ok=True)


def _draft_path() -> Path:
    """Return a stable draft file path based on the current user role."""
    rol = st.session_state.get("rol", "operativo")
    return DRAFT_DIR / f"draft_{rol}.json"


def _save_draft():
    """Persist current audit state to a JSON file for later resumption."""
    data = {
        "local_name": st.session_state.get("local_name", ""),
        "audit_date": st.session_state.get("audit_date", ""),
        "results": [],
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    for entry in st.session_state.get("results", []):
        serializable = {
            "criterion": entry["criterion"],
            "result": entry["result"],
            "filename": entry.get("filename", ""),
            "timestamp": entry.get("timestamp", ""),
        }
        data["results"].append(serializable)

    _draft_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    st.toast("Progreso guardado", icon="💾")


def _load_draft() -> dict | None:
    """Load a previously saved draft, or return None."""
    path = _draft_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _delete_draft():
    """Remove the draft file."""
    path = _draft_path()
    if path.exists():
        path.unlink()


def _get_unique_evaluated_items() -> set[str]:
    """Return set of unique item IDs that have been evaluated in this session."""
    return {r["criterion"]["id"] for r in st.session_state.get("results", [])}

STATUS_COLORS = {
    "Conforme": "#2ecc71",
    "Observación": "#f39c12",
    "No Conforme": "#e74c3c",
}

STATUS_ICONS = {
    "Conforme": "✅",
    "Observación": "⚠️",
    "No Conforme": "❌",
}

SYSTEM_PROMPT = """\
Sos un auditor experto de franquicias Grido (heladerías). Tu tarea es analizar \
fotografías del local y evaluar si cumplen con los criterios de la guía de \
auditoría operativa. Para cada foto, debés determinar si el ítem auditado está:

- **Conforme**: cumple con todos los requisitos.
- **Observación**: presenta desvíos leves que no comprometen la imagen ni la seguridad.
- **No Conforme**: presenta defectos graves, visibles, o que comprometen la seguridad/higiene.

Respondé SIEMPRE en formato JSON con esta estructura exacta:
{
  "status": "Conforme" | "Observación" | "No Conforme",
  "justificacion": "Explicación breve de por qué se asigna ese estado, haciendo referencia a lo que se observa en la foto.",
  "detalles_observados": ["detalle 1", "detalle 2", ...],
  "recomendaciones": ["recomendación 1", ...]
}

Sé riguroso pero justo. Si la foto no permite evaluar claramente el ítem, indicalo \
en la justificación y asigná "Observación" por precaución. \
No inventes lo que no se ve; solo evaluá lo visible en la imagen.

IMPORTANTE: Cuando el auditor humano haya corregido evaluaciones anteriores tuyas \
sobre este mismo ítem, se te proporcionarán como ejemplos de referencia. \
Prestá mucha atención a esas correcciones: reflejan el criterio real del auditor \
y debés ajustar tu evaluación para ser consistente con ese criterio. \
Si la IA evaluó "Observación" pero el auditor corrigió a "No Conforme", eso \
significa que debés ser más estricto en casos similares.\
"""


# ── Session state ───────────────────────────────────────────────────────
def _init_state():
    if "results" not in st.session_state:
        st.session_state.results: list[dict] = []
    if "audit_date" not in st.session_state:
        st.session_state.audit_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    if "local_name" not in st.session_state:
        st.session_state.local_name = ""
    if "draft_checked" not in st.session_state:
        st.session_state.draft_checked = False
    if "audit_finalized" not in st.session_state:
        st.session_state.audit_finalized = False


_init_state()

# ── Draft recovery dialog ────────────────────────────────────────────────
if not st.session_state.draft_checked:
    st.session_state.draft_checked = True
    draft = _load_draft()
    if draft and draft.get("results") and not st.session_state.results:
        st.session_state["_pending_draft"] = draft

if "_pending_draft" in st.session_state:
    draft = st.session_state["_pending_draft"]
    n_items = len({r["criterion"]["id"] for r in draft["results"]})
    st.info(
        f"Se encontró una auditoría en curso guardada el **{draft['saved_at']}** "
        f"para el local **{draft.get('local_name', '—')}** con **{n_items}/{TOTAL_ITEMS}** ítems evaluados."
    )
    col_resume, col_discard = st.columns(2)
    with col_resume:
        if st.button("▶️ Continuar auditoría", type="primary", use_container_width=True):
            st.session_state.results = draft["results"]
            st.session_state.local_name = draft.get("local_name", "")
            st.session_state.audit_date = draft.get("audit_date", datetime.now().strftime("%Y-%m-%d %H:%M"))
            st.session_state.audit_finalized = False
            del st.session_state["_pending_draft"]
            st.rerun()
    with col_discard:
        if st.button("🗑️ Descartar y empezar de cero", use_container_width=True):
            _delete_draft()
            del st.session_state["_pending_draft"]
            st.rerun()
    st.stop()


# ── Navigation helper ────────────────────────────────────────────────────
def _go_to_prev_item() -> bool:
    """Schedule navigation to the previous audit item."""
    section_keys = list(SECTIONS.keys())
    current_section = st.session_state.get("aud_section", section_keys[0])
    current_criterion = st.session_state.get("aud_criterion", "")

    criteria_ids = [c["id"] for c in get_criteria_by_section(current_section)]

    if current_criterion in criteria_ids:
        idx = criteria_ids.index(current_criterion)
        if idx - 1 >= 0:
            st.session_state._nav_section = current_section
            st.session_state._nav_criterion = criteria_ids[idx - 1]
            return True

    sec_idx = section_keys.index(current_section) if current_section in section_keys else 0
    if sec_idx - 1 >= 0:
        prev_sec = section_keys[sec_idx - 1]
        prev_criteria = get_criteria_by_section(prev_sec)
        if prev_criteria:
            st.session_state._nav_section = prev_sec
            st.session_state._nav_criterion = prev_criteria[-1]["id"]
            return True

    return False


def _advance_to_next_item():
    """Schedule navigation to the next audit item (consumed before widgets render)."""
    section_keys = list(SECTIONS.keys())
    current_section = st.session_state.get("aud_section", section_keys[0])
    current_criterion = st.session_state.get("aud_criterion", "")

    criteria_ids = [c["id"] for c in get_criteria_by_section(current_section)]

    if current_criterion in criteria_ids:
        idx = criteria_ids.index(current_criterion)
        if idx + 1 < len(criteria_ids):
            st.session_state._nav_section = current_section
            st.session_state._nav_criterion = criteria_ids[idx + 1]
            return True

    sec_idx = section_keys.index(current_section) if current_section in section_keys else 0
    if sec_idx + 1 < len(section_keys):
        next_sec = section_keys[sec_idx + 1]
        next_criteria = get_criteria_by_section(next_sec)
        if next_criteria:
            st.session_state._nav_section = next_sec
            st.session_state._nav_criterion = next_criteria[0]["id"]
            return True

    return False


# ── AI analysis ─────────────────────────────────────────────────────────
def _encode_image(uploaded_file) -> str:
    return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")


def _build_corrections_context(corrections: list[dict]) -> str:
    """Build a text block with past corrections to inject in the prompt."""
    if not corrections:
        return ""
    lines = [
        "\n\n## Correcciones previas del auditor humano para este ítem\n"
        "Usá estos ejemplos como referencia para calibrar tu evaluación:\n"
    ]
    for i, c in enumerate(corrections, 1):
        lines.append(
            f"**Ejemplo {i}:** La IA evaluó **{c['ai_status']}** pero el auditor "
            f"corrigió a **{c['corrected_status']}**.\n"
            f"- Justificación IA: {c.get('ai_justificacion', '—')}\n"
            f"- Nota del auditor: {c.get('correction_notes', '—')}\n"
        )
    return "\n".join(lines)


def analyze_photo(
    api_key: str,
    image_file,
    criterion: dict,
    model: str = "gpt-4o",
    corrections: list[dict] | None = None,
) -> dict:
    client = OpenAI(api_key=api_key)
    b64 = _encode_image(image_file)
    mime = image_file.type or "image/jpeg"

    corrections_ctx = _build_corrections_context(corrections or [])

    user_prompt = (
        f"## Ítem a evaluar: {criterion['id']} — {criterion['name']}\n\n"
        f"**Criterios de CONFORME:**\n{criterion['conforme']}\n\n"
        f"**Criterios de OBSERVACIÓN:**\n{criterion['observacion']}\n\n"
        f"**Criterios de NO CONFORME:**\n{criterion['no_conforme']}\n\n"
        f"{corrections_ctx}\n\n"
        "Analizá la siguiente fotografía y evaluá si el ítem está Conforme, "
        "Observación o No Conforme. Respondé en JSON."
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{b64}",
                            "detail": "high",
                        },
                    },
                ],
            },
        ],
        max_tokens=1000,
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "status": "Observación",
            "justificacion": raw,
            "detalles_observados": [],
            "recomendaciones": ["No se pudo parsear la respuesta de la IA."],
        }


# ── UI helpers ──────────────────────────────────────────────────────────
def _status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, "#95a5a6")
    icon = STATUS_ICONS.get(status, "❔")
    return (
        f'<span style="background:{color};color:white;padding:4px 12px;'
        f'border-radius:12px;font-weight:600;font-size:0.95rem;">'
        f"{icon} {status}</span>"
    )


def _render_result(result: dict, criterion: dict, idx: int):
    status = result.get("status", "Observación")
    color = STATUS_COLORS.get(status, "#95a5a6")

    st.markdown(
        f"<div style='border-left:4px solid {color};padding:12px 16px;"
        f"margin-bottom:16px;background:#fafafa;border-radius:4px;'>"
        f"<h4 style='margin:0 0 8px 0;'>{criterion['id']} — {criterion['name']} "
        f"{_status_badge(status)}</h4>"
        f"<p><strong>Justificación:</strong> {result.get('justificacion', '—')}</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    details = result.get("detalles_observados", [])
    recs = result.get("recomendaciones", [])

    col1, col2 = st.columns(2)
    with col1:
        if details:
            st.markdown("**Detalles observados:**")
            for d in details:
                st.markdown(f"- {d}")
    with col2:
        if recs:
            st.markdown("**Recomendaciones:**")
            for r in recs:
                st.markdown(f"- {r}")


_STATUS_SEVERITY = {"Conforme": 0, "Observación": 1, "No Conforme": 2}


def _worst_status(statuses: list[str]) -> str:
    """Return the most severe status from a list (No Conforme > Observación > Conforme)."""
    return max(statuses, key=lambda s: _STATUS_SEVERITY.get(s, 1))


def _build_report_df() -> pd.DataFrame:
    """Build a consolidated report: one row per item, worst status wins."""
    items: dict[str, dict] = {}
    for r in st.session_state.results:
        item_id = r["criterion"]["id"]
        status = r["result"]["status"]
        if item_id not in items:
            items[item_id] = {
                "Ítem": item_id,
                "Nombre": r["criterion"]["name"],
                "Sección": get_section_name(r["criterion"]["section"]),
                "Estado": status,
                "Justificación": r["result"].get("justificacion", ""),
                "Detalles": "; ".join(r["result"].get("detalles_observados", [])),
                "Recomendaciones": "; ".join(r["result"].get("recomendaciones", [])),
                "Fotos": 1,
                "Fecha": r.get("timestamp", ""),
            }
        else:
            prev = items[item_id]
            prev["Fotos"] += 1
            if _STATUS_SEVERITY.get(status, 1) > _STATUS_SEVERITY.get(prev["Estado"], 1):
                prev["Estado"] = status
                prev["Justificación"] = r["result"].get("justificacion", "")
                prev["Detalles"] = "; ".join(r["result"].get("detalles_observados", []))
                prev["Recomendaciones"] = "; ".join(r["result"].get("recomendaciones", []))
    return pd.DataFrame(list(items.values()))


def _to_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Auditoría")
    return buf.getvalue()


# ── Sidebar ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.caption("Auditoría interna — evaluación manual")

    st.divider()

    local_name = st.selectbox(
        "📍 Local",
        LOCALES,
        index=LOCALES.index(st.session_state.local_name) if st.session_state.local_name in LOCALES else 0,
    )
    st.session_state.local_name = local_name

    tipo_auditoria = st.selectbox(
        "Tipo de auditoría",
        TIPOS_AUDITORIA,
        format_func=lambda t: t.replace("_", " ").title(),
    )

    st.divider()

    _section_keys = list(SECTIONS.keys())
    _nav_sec = st.session_state.pop("_nav_section", None)
    _nav_crit = st.session_state.pop("_nav_criterion", None)

    if _nav_sec is not None:
        st.session_state.pop("aud_section", None)
        st.session_state.pop("aud_criterion", None)

    _sec_default = _section_keys.index(_nav_sec) if _nav_sec in _section_keys else 0
    section = st.selectbox(
        "Sección a auditar",
        _section_keys,
        index=_sec_default,
        format_func=lambda s: f"{s}. {SECTIONS[s]}",
        key="aud_section",
    )

    section_criteria = get_criteria_by_section(section)
    _crit_ids = [c["id"] for c in section_criteria]
    _crit_default = _crit_ids.index(_nav_crit) if _nav_crit and _nav_crit in _crit_ids else 0
    criterion_id = st.selectbox(
        "Ítem específico",
        _crit_ids,
        index=_crit_default,
        format_func=lambda cid: f"{cid} — {get_criterion_by_id(cid)['name'][:60]}",
        key="aud_criterion",
    )

    selected_criterion = get_criterion_by_id(criterion_id)

    st.divider()
    evaluated_ids = _get_unique_evaluated_items()
    n_evaluated = len(evaluated_ids)
    total_photos = len(st.session_state.results)
    obs_ids = set()
    nc_ids = set()
    conf_ids = set()
    for r in st.session_state.results:
        item_id = r["criterion"]["id"]
        status = r["result"]["status"]
        if status == "No Conforme":
            nc_ids.add(item_id)
        elif status == "Observación":
            obs_ids.add(item_id)
        else:
            conf_ids.add(item_id)
    nc_ids_final = nc_ids
    obs_ids_final = obs_ids - nc_ids
    conf_ids_final = conf_ids - nc_ids - obs_ids

    st.markdown(f"**Progreso: {n_evaluated}/{TOTAL_ITEMS} ítems**")
    st.progress(n_evaluated / TOTAL_ITEMS if TOTAL_ITEMS > 0 else 0)

    cols = st.columns(3)
    cols[0].metric("✅", len(conf_ids_final))
    cols[1].metric("⚠️", len(obs_ids_final))
    cols[2].metric("❌", len(nc_ids_final))

    if total_photos > 0:
        st.caption(f"📷 {total_photos} foto(s) analizadas en total")

    st.divider()
    st.markdown("**Finalizar auditoría**")

    all_complete = n_evaluated >= TOTAL_ITEMS
    if st.button(
        f"✅ Finalizar completo ({n_evaluated}/{TOTAL_ITEMS})",
        use_container_width=True,
        disabled=not all_complete,
        type="primary" if all_complete else "secondary",
        help="Se habilita cuando los 61 ítems están evaluados" if not all_complete else "Finalizar la auditoría completa",
    ):
        _delete_draft()
        st.session_state.audit_finalized = True
        if db.is_connected() and local_name:
            try:
                fecha_now = datetime.now().strftime("%Y-%m")
                db.upsert_auditoria(
                    local=local_name,
                    fecha=fecha_now,
                    tipo=tipo_auditoria,
                    created_by=st.session_state.get("rol", "operativo"),
                )
            except Exception:
                pass
        st.success(f"Auditoría COMPLETA finalizada con {n_evaluated}/{TOTAL_ITEMS} ítems.")

    if st.button(
        "⚠️ Finalizar parcial",
        use_container_width=True,
        disabled=n_evaluated == 0,
        help="Cerrar la auditoría con los ítems evaluados hasta ahora",
    ):
        _delete_draft()
        st.session_state.audit_finalized = True
        if db.is_connected() and local_name:
            try:
                fecha_now = datetime.now().strftime("%Y-%m")
                db.upsert_auditoria(
                    local=local_name,
                    fecha=fecha_now,
                    tipo="parcial",
                    created_by=st.session_state.get("rol", "operativo"),
                )
            except Exception:
                pass
        st.warning(f"Auditoría PARCIAL finalizada con {n_evaluated}/{TOTAL_ITEMS} ítems.")

    st.divider()
    if st.button("🔄 Resetear auditoría", use_container_width=True, type="secondary"):
        _delete_draft()
        st.session_state.results = []
        st.session_state.audit_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.session_state.audit_finalized = False
        st.session_state.draft_checked = True
        st.rerun()


# ── Main area ───────────────────────────────────────────────────────────
tab_audit, tab_report, tab_criteria = st.tabs(
    ["📸 Auditar", "📊 Reporte", "📋 Criterios"]
)

# ─── Tab: Auditar ───────────────────────────────────────────────────────
with tab_audit:
    st.header(f"{selected_criterion['id']} — {selected_criterion['name']}")
    st.caption(f"Check {selected_criterion['check']} · Sección {section}: {SECTIONS[section]}")

    with st.expander("📖 Ver criterios de evaluación", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                "<div style='background:#2ecc71;color:white;padding:8px 12px;"
                "border-radius:8px;font-weight:600;text-align:center;'>CONFORME</div>",
                unsafe_allow_html=True,
            )
            st.markdown(selected_criterion["conforme"] or "_Sin criterio específico_")
        with c2:
            st.markdown(
                "<div style='background:#f39c12;color:white;padding:8px 12px;"
                "border-radius:8px;font-weight:600;text-align:center;'>OBSERVACIÓN</div>",
                unsafe_allow_html=True,
            )
            st.markdown(selected_criterion["observacion"] or "_Sin criterio específico_")
        with c3:
            st.markdown(
                "<div style='background:#e74c3c;color:white;padding:8px 12px;"
                "border-radius:8px;font-weight:600;text-align:center;'>NO CONFORME</div>",
                unsafe_allow_html=True,
            )
            st.markdown(selected_criterion["no_conforme"] or "_Sin criterio específico_")

    st.divider()

    # ── Navegación wizard (tablet) ────────────────────────────────
    _is_first = False
    _is_last = False
    _section_keys_nav = list(SECTIONS.keys())
    _current_sec_nav = st.session_state.get("aud_section", _section_keys_nav[0])
    _current_crit_nav = st.session_state.get("aud_criterion", "")
    _crit_ids_nav = [c["id"] for c in get_criteria_by_section(_current_sec_nav)]
    if _crit_ids_nav:
        _is_first = (
            _section_keys_nav.index(_current_sec_nav) == 0
            and _crit_ids_nav.index(_current_crit_nav) == 0
            if _current_crit_nav in _crit_ids_nav else False
        )
        _is_last = (
            _section_keys_nav.index(_current_sec_nav) == len(_section_keys_nav) - 1
            and _crit_ids_nav.index(_current_crit_nav) == len(_crit_ids_nav) - 1
            if _current_crit_nav in _crit_ids_nav else False
        )

    _evaluated_ids = _get_unique_evaluated_items()
    _total_nav = len(CRITERIA)
    _done_nav = len(_evaluated_ids)
    st.progress(
        _done_nav / _total_nav if _total_nav else 0,
        text=f"**{_done_nav} / {_total_nav}** ítems evaluados",
    )

    _nav_col1, _nav_col2 = st.columns(2)
    with _nav_col1:
        if st.button(
            "← Anterior",
            use_container_width=True,
            disabled=_is_first,
            key="btn_prev_top",
        ):
            _go_to_prev_item()
            st.rerun()
    with _nav_col2:
        if st.button(
            "Siguiente →",
            use_container_width=True,
            disabled=_is_last,
            key="btn_next_top",
            type="primary",
        ):
            _advance_to_next_item()
            st.rerun()

    st.divider()

    # ── Cargar fotos desde MongoDB o subir manualmente ────────────
    db_photos = []
    if db.is_connected() and local_name:
        fecha_audit = datetime.now().strftime("%Y-%m")
        db_photos = db.get_photos_for_item(local_name, fecha_audit, criterion_id)

    if db_photos:
        st.markdown(
            f"📦 **{len(db_photos)} foto(s) disponibles**, cargadas desde 📸 Captura de Fotos "
            f"para el local *{local_name}*"
        )
        photo_cols = st.columns(min(len(db_photos), 4))
        for i, p in enumerate(db_photos):
            with photo_cols[i % len(photo_cols)]:
                st.image(p["photo_data"], caption=p["photo_name"], use_container_width=True)
    else:
        st.info("No hay fotos cargadas todavía para este ítem. Podés subir alguna acá abajo o cargarla desde 📸 Captura de Fotos.")

    uploaded_files = st.file_uploader(
        "O subí fotos manualmente",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key=f"upload_{criterion_id}",
    )

    if uploaded_files:
        upload_cols = st.columns(min(len(uploaded_files), 4))
        for i, f in enumerate(uploaded_files):
            with upload_cols[i % len(upload_cols)]:
                st.image(f, caption=f.name, use_container_width=True)

    all_photo_names = [p["photo_name"] for p in db_photos] + [f.name for f in (uploaded_files or [])]

    st.divider()

    # ── Evaluación manual ───────────────────────────────────────────
    st.subheader("✍️ Evaluación")

    existing_idx = next(
        (i for i, r in enumerate(st.session_state.results) if r["criterion"]["id"] == criterion_id),
        None,
    )

    # Si se aceptó una sugerencia de IA (ver más abajo), precargar los widgets
    # ANTES de instanciarlos — Streamlit no permite tocar el session_state de
    # un widget después de haberlo creado en el mismo ciclo de ejecución.
    _pending_beta = st.session_state.pop(f"_apply_beta_{criterion_id}", None)
    if _pending_beta:
        st.session_state[f"eval_status_{criterion_id}"] = _pending_beta.get("status", "Observación")
        st.session_state[f"eval_nota_{criterion_id}"] = _pending_beta.get("justificacion", "")

    _status_key = f"eval_status_{criterion_id}"
    if _status_key not in st.session_state:
        st.session_state[_status_key] = "Conforme"
    eval_status = st.session_state[_status_key]

    def _sel(status: str) -> str:
        return "sel" if status == eval_status else "unsel"

    st.caption("Estado del ítem")
    bcol1, bcol2, bcol3 = st.columns(3)
    with bcol1:
        if st.button(
            "✅ Conforme", use_container_width=True, key=f"aud_btn_conforme_{criterion_id}_{_sel('Conforme')}"
        ):
            st.session_state[_status_key] = "Conforme"
            st.rerun()
    with bcol2:
        if st.button(
            "⚠️ Observación", use_container_width=True, key=f"aud_btn_observacion_{criterion_id}_{_sel('Observación')}"
        ):
            st.session_state[_status_key] = "Observación"
            st.rerun()
    with bcol3:
        if st.button(
            "❌ No conforme", use_container_width=True, key=f"aud_btn_noconforme_{criterion_id}_{_sel('No Conforme')}"
        ):
            st.session_state[_status_key] = "No Conforme"
            st.rerun()

    nota_needed = eval_status != "Conforme"
    eval_nota = st.text_area(
        "Nota — qué se observó" + (" (obligatoria)" if nota_needed else " (opcional)"),
        key=f"eval_nota_{criterion_id}",
        placeholder="Ej: Exhibidora fuera de lugar, falta cartel de precios...",
    )

    nota_ok = (not nota_needed) or bool(eval_nota.strip())
    if nota_needed and not nota_ok:
        st.warning("Agregá una nota breve describiendo el desvío antes de confirmar.")

    _create_desvio_checked = False
    if nota_needed and db.is_connected():
        _create_desvio_checked = st.checkbox(
            f"Crear desvío para {criterion_id} (estado: {eval_status})",
            value=True,
            key=f"crear_desvio_{criterion_id}",
        )

    confirm_col1, confirm_col2 = st.columns([3, 1])
    with confirm_col1:
        confirm_clicked = st.button(
            "✅ Confirmar y siguiente",
            type="primary",
            use_container_width=True,
            disabled=not nota_ok,
        )
    with confirm_col2:
        skip_clicked = st.button("Saltar ítem →", use_container_width=True)

    if confirm_clicked:
        fecha_now = datetime.now().strftime("%Y-%m")
        result = {
            "status": eval_status,
            "justificacion": eval_nota.strip(),
            "detalles_observados": [],
            "recomendaciones": [],
        }
        entry = {
            "criterion": selected_criterion,
            "result": result,
            "filename": ", ".join(all_photo_names) if all_photo_names else "sin foto",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        if existing_idx is not None:
            st.session_state.results[existing_idx] = entry
        else:
            st.session_state.results.append(entry)
        _save_draft()

        if db.is_connected() and local_name:
            try:
                db.save_audit_result(
                    local=local_name,
                    fecha=fecha_now,
                    section=selected_criterion["section"],
                    item_id=selected_criterion["id"],
                    item_name=selected_criterion["name"],
                    result=result,
                    filename=entry["filename"],
                    model="manual",
                )
            except Exception as e:
                st.warning(f"No se pudo guardar el resultado en MongoDB: {e}")

        # Si se había pedido una sugerencia de IA para este ítem y el criterio
        # final difiere, se guarda como corrección (útil si en el futuro se
        # retoma la calibración del modelo).
        _beta_result_used = st.session_state.get(f"beta_result_{criterion_id}")
        if _beta_result_used and db.is_connected():
            ai_status = _beta_result_used.get("status", "Observación")
            if ai_status != eval_status:
                try:
                    db.save_correction(
                        item_id=selected_criterion["id"],
                        item_name=selected_criterion["name"],
                        ai_status=ai_status,
                        corrected_status=eval_status,
                        ai_justificacion=_beta_result_used.get("justificacion", ""),
                        correction_notes=eval_nota.strip(),
                        local=local_name,
                        fecha=fecha_now,
                    )
                except Exception:
                    pass

        if _create_desvio_checked and db.is_connected():
            try:
                nivel = "rojo" if eval_status == "No Conforme" else "amarillo"
                prioridad = "alta" if eval_status == "No Conforme" else "media"
                db.create_desvio(
                    auditoria_fecha=fecha_now,
                    local=local_name,
                    seccion=selected_criterion["section"],
                    item_codigo=selected_criterion["id"],
                    item_descripcion=selected_criterion["name"][:120],
                    nivel=nivel,
                    ai_justificacion=eval_nota.strip(),
                    prioridad=prioridad,
                )
            except Exception:
                pass

        if db.is_connected() and local_name:
            try:
                db.upsert_auditoria(
                    local=local_name,
                    fecha=fecha_now,
                    tipo=tipo_auditoria,
                    created_by=st.session_state.get("rol", "operativo"),
                )
            except Exception:
                pass

        if _advance_to_next_item():
            st.rerun()
        else:
            st.success("Último ítem confirmado. Revisá el Reporte.")

    if skip_clicked:
        if _advance_to_next_item():
            st.rerun()

    if existing_idx is not None:
        _prev = st.session_state.results[existing_idx]
        st.caption(
            f"Última evaluación guardada: {STATUS_ICONS.get(_prev['result']['status'], '')} "
            f"{_prev['result']['status']} — {_prev['timestamp']}"
        )

    # ── 🧪 Sugerencia con IA (opcional, beta) ────────────────────────
    with st.expander("🧪 Sugerencia con IA (opcional, beta)", expanded=False):
        st.caption(
            "Herramienta experimental y opcional: la IA puede sugerir un estado a partir de "
            "una foto, pero **vos definís la evaluación final arriba**. Se desactivó como "
            "paso obligatorio porque tendía a ser repetitiva y poco precisa; se deja disponible "
            "como segunda opinión."
        )
        _default_key = st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else ""
        beta_api_key = st.text_input(
            "🔑 OpenAI API Key", value=_default_key, type="password", key="beta_api_key"
        )
        beta_model = st.selectbox(
            "Modelo de IA", ["gpt-4o", "gpt-4o-mini"], key="beta_model"
        )

        beta_photo = db_photos[0] if db_photos else None
        beta_upload = uploaded_files[0] if uploaded_files else None
        suggest_disabled = not beta_api_key or not (beta_photo or beta_upload)

        if st.button("🔍 Pedir sugerencia IA", disabled=suggest_disabled, key=f"beta_suggest_{criterion_id}"):
            try:
                if beta_photo:
                    img_file = io.BytesIO(beta_photo["photo_data"])
                    img_file.name = beta_photo["photo_name"]
                    img_file.type = "image/jpeg"
                    img_file.getvalue = lambda d=beta_photo["photo_data"]: d
                else:
                    img_file = beta_upload

                with st.spinner("Consultando IA..."):
                    ai_result = analyze_photo(
                        api_key=beta_api_key,
                        image_file=img_file,
                        criterion=selected_criterion,
                        model=beta_model,
                    )
                st.session_state[f"beta_result_{criterion_id}"] = ai_result
            except Exception as exc:
                st.error(f"Error al consultar la IA: {exc}")

        _beta_result = st.session_state.get(f"beta_result_{criterion_id}")
        if _beta_result:
            _render_result(_beta_result, selected_criterion, 0)
            if st.button("Usar esta sugerencia como base", key=f"beta_use_{criterion_id}"):
                st.session_state[f"_apply_beta_{criterion_id}"] = _beta_result
                st.rerun()

    # ── Ítems ya evaluados ────────────────────────────────────────────
    other_results = [r for r in st.session_state.results if r["criterion"]["id"] != criterion_id]
    if other_results:
        st.divider()
        with st.expander(f"📋 Ítems ya evaluados ({len(other_results)})", expanded=False):
            for entry in reversed(other_results):
                _render_result(entry["result"], entry["criterion"], 0)

    # ── Navegación wizard inferior ─────────────────────────────────
    st.divider()
    _nav_bot1, _nav_bot2 = st.columns(2)
    with _nav_bot1:
        if st.button(
            "← Anterior",
            use_container_width=True,
            disabled=_is_first,
            key="btn_prev_bot",
        ):
            _go_to_prev_item()
            st.rerun()
    with _nav_bot2:
        if st.button(
            "Siguiente →",
            use_container_width=True,
            disabled=_is_last,
            key="btn_next_bot",
            type="primary",
        ):
            _advance_to_next_item()
            st.rerun()

# ─── Tab: Reporte ───────────────────────────────────────────────────────
with tab_report:
    st.header("📊 Reporte de Auditoría")

    report_source = "session"
    db_report_results = []

    if db.is_connected():
        history = db.get_audit_history()
        if history:
            audit_options = [f"{h['local']} — {h['fecha']}" for h in history]
            audit_options.insert(0, "Sesión actual")
            selected_audit = st.selectbox("Seleccionar auditoría", audit_options)
            if selected_audit != "Sesión actual":
                idx = audit_options.index(selected_audit) - 1
                sel = history[idx]
                db_report_results = db.get_audit_results(sel["local"], sel["fecha"])
                report_source = "db"

    if report_source == "db" and db_report_results:
        items_db: dict[str, dict] = {}
        for r in db_report_results:
            item_id = r["item_id"]
            status = r["status"]
            if item_id not in items_db:
                items_db[item_id] = {
                    "Ítem": item_id,
                    "Nombre": r.get("item_name", ""),
                    "Sección": get_section_name(r.get("section", "")),
                    "Estado": status,
                    "Justificación": r.get("justificacion", ""),
                    "Detalles": "; ".join(r.get("detalles_observados", [])),
                    "Recomendaciones": "; ".join(r.get("recomendaciones", [])),
                    "Fotos": 1,
                    "Fecha": r.get("analyzed_at", ""),
                }
            else:
                prev = items_db[item_id]
                prev["Fotos"] += 1
                if _STATUS_SEVERITY.get(status, 1) > _STATUS_SEVERITY.get(prev["Estado"], 1):
                    prev["Estado"] = status
                    prev["Justificación"] = r.get("justificacion", "")
                    prev["Detalles"] = "; ".join(r.get("detalles_observados", []))
                    prev["Recomendaciones"] = "; ".join(r.get("recomendaciones", []))
        df = pd.DataFrame(list(items_db.values()))

        sel_h = history[audit_options.index(selected_audit) - 1]
        st.markdown(
            f"**Local:** {sel_h['local']} · "
            f"**Período:** {sel_h['fecha']} · "
            f"**Ítems evaluados:** {sel_h['total']} · "
            f"**Conformidad:** {sel_h['pct_conforme']}%"
        )
    elif st.session_state.results:
        df = _build_report_df()
        st.markdown(
            f"**Local:** {st.session_state.local_name or '—'} · "
            f"**Fecha:** {st.session_state.audit_date} · "
            f"**Ítems evaluados:** {len(st.session_state.results)}"
        )
    else:
        df = None
        st.info("Todavía no hay resultados. Analizá al menos una foto en la pestaña Auditar.")

    if df is not None and not df.empty:
        st.divider()

        # ── Gráfico de barras por sección (colores Grido) ─────────────────
        try:
            import plotly.graph_objects as go

            _SECTION_COLORS = {
                "A": "#0033CC",
                "B": "#00AEEF",
                "C": "#8DC63F",
                "D": "#E8185A",
                "E": "#F5841F",
            }

            if report_source == "db" and db_report_results:
                _chart_local = sel_h["local"]
                _chart_fecha = sel_h["fecha"]
            else:
                _chart_local = st.session_state.get("local_name", "")
                _chart_fecha = datetime.now().strftime("%Y-%m")
            _scores_for_chart = db.calculate_section_scores(_chart_local, _chart_fecha) or {}
            if _scores_for_chart:
                _sec_labels = []
                _sec_values = []
                _sec_colors = []
                for _sec_key in sorted(_scores_for_chart.keys()):
                    _sec_labels.append(f"Sección {_sec_key}")
                    _val = _scores_for_chart[_sec_key]
                    _sec_values.append(round(_val * 100, 1) if _val <= 1 else round(_val, 1))
                    _sec_colors.append(_SECTION_COLORS.get(_sec_key, "#0033CC"))

                _fig = go.Figure(
                    go.Bar(
                        x=_sec_values,
                        y=_sec_labels,
                        orientation="h",
                        marker_color=_sec_colors,
                        text=[f"{v:.1f}%" for v in _sec_values],
                        textposition="outside",
                    )
                )
                _fig.update_layout(
                    title="Puntaje por sección",
                    xaxis=dict(range=[0, 110], showgrid=False, visible=False),
                    yaxis=dict(autorange="reversed"),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=10, r=40, t=40, b=10),
                    height=260,
                    font=dict(size=13),
                )
                st.plotly_chart(_fig, use_container_width=True)
        except Exception:
            pass  # Si Plotly no está disponible o los datos faltan, se omite el gráfico silenciosamente

        summary_col1, summary_col2 = st.columns([1, 2])
        with summary_col1:
            status_counts = df["Estado"].value_counts()
            for status_val in ["Conforme", "Observación", "No Conforme"]:
                count = status_counts.get(status_val, 0)
                pct = (count / len(df) * 100) if len(df) else 0
                icon = STATUS_ICONS.get(status_val, "")
                st.markdown(
                    f"<div style='display:flex;align-items:center;margin-bottom:8px;'>"
                    f"<span style='font-size:1.5rem;margin-right:8px;'>{icon}</span>"
                    f"<span style='font-size:1.1rem;font-weight:600;'>{status_val}: {count} ({pct:.0f}%)</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            if report_source == "session":
                total_items = len(CRITERIA)
                coverage = len(set(r["criterion"]["id"] for r in st.session_state.results))
                st.metric("Cobertura", f"{coverage}/{total_items} ítems")
            else:
                unique_items = df["Ítem"].nunique()
                total_items = len(CRITERIA)
                st.metric("Cobertura", f"{unique_items}/{total_items} ítems")

        with summary_col2:
            for sec_key, sec_name in SECTIONS.items():
                sec_results = df[df["Sección"] == sec_name]
                if sec_results.empty:
                    continue
                sec_conformes = (sec_results["Estado"] == "Conforme").sum()
                sec_total = len(sec_results)
                pct = sec_conformes / sec_total * 100 if sec_total else 0
                st.markdown(
                    f"**{sec_key}. {sec_name}** — {sec_conformes}/{sec_total} conformes ({pct:.0f}%)"
                )
                st.progress(pct / 100)

        st.divider()
        st.subheader("Detalle por ítem")
        st.dataframe(
            df[["Ítem", "Nombre", "Estado", "Justificación"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Estado": st.column_config.TextColumn(width="small"),
            },
        )

        st.divider()
        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            excel_bytes = _to_excel(df)
            st.download_button(
                "📥 Descargar Excel",
                data=excel_bytes,
                file_name=f"auditoria_grido_{datetime.now():%Y%m%d_%H%M}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with col_dl2:
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Descargar CSV",
                data=csv_data,
                file_name=f"auditoria_grido_{datetime.now():%Y%m%d_%H%M}.csv",
                mime="text/csv",
                use_container_width=True,
            )

# ─── Tab: Criterios ────────────────────────────────────────────────────
with tab_criteria:
    st.header("📋 Guía completa de criterios")
    st.caption("Referencia: Auditorías Operativas Abril 2025")

    for sec_key, sec_name in SECTIONS.items():
        with st.expander(f"**{sec_key}. {sec_name}**", expanded=False):
            for c in get_criteria_by_section(sec_key):
                st.markdown(f"### {c['id']} — {c['name']}")
                st.caption(f"Check {c['check']}")
                cols = st.columns(3)
                with cols[0]:
                    st.success("**CONFORME**")
                    st.markdown(c["conforme"] or "_—_")
                with cols[1]:
                    st.warning("**OBSERVACIÓN**")
                    st.markdown(c["observacion"] or "_—_")
                with cols[2]:
                    st.error("**NO CONFORME**")
                    st.markdown(c["no_conforme"] or "_—_")
                st.divider()

# ── Footer ──────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Grido Audit Vision · Herramienta de autocontrol interno · "
    "Evaluación manual del responsable operativo — no reemplaza la auditoría oficial de la franquicia."
)
