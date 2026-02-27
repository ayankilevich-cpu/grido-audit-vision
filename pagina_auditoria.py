"""
Grido Audit Vision — Página de auditoría con IA.
Sube fotos de tu heladería y validá el cumplimiento de los criterios
de la Guía de Auditoría Operativa Grido.
"""

from __future__ import annotations

import base64
import io
import json
from datetime import datetime

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


_init_state()


# ── Navigation helper ────────────────────────────────────────────────────
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
    st.caption("Auditoría interna con IA")

    st.divider()

    _default_key = st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else ""
    api_key = st.text_input(
        "🔑 OpenAI API Key",
        value=_default_key,
        type="password",
        help=(
            "Se necesita una clave de OpenAI con acceso a gpt-4o. "
            "En Streamlit Cloud se puede configurar en Settings → Secrets."
        ),
    )

    model_choice = st.selectbox(
        "Modelo de IA",
        ["gpt-4o", "gpt-4o-mini"],
        help="gpt-4o es más preciso; gpt-4o-mini es más rápido y económico.",
    )

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
    total = len(st.session_state.results)
    conformes = sum(1 for r in st.session_state.results if r["result"]["status"] == "Conforme")
    obs = sum(1 for r in st.session_state.results if r["result"]["status"] == "Observación")
    no_conf = sum(1 for r in st.session_state.results if r["result"]["status"] == "No Conforme")

    st.metric("Ítems evaluados", total)
    cols = st.columns(3)
    cols[0].metric("✅", conformes)
    cols[1].metric("⚠️", obs)
    cols[2].metric("❌", no_conf)

    if st.button("🗑️ Reiniciar auditoría", use_container_width=True):
        st.session_state.results = []
        st.session_state.audit_date = datetime.now().strftime("%Y-%m-%d %H:%M")
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

    # ── Cargar fotos desde MongoDB o subir manualmente ────────────
    db_photos = []
    if db.is_connected() and local_name:
        fecha_audit = datetime.now().strftime("%Y-%m")
        db_photos = db.get_photos_for_item(local_name, fecha_audit, criterion_id)

    if db_photos:
        st.markdown(
            f"📦 **{len(db_photos)} foto(s) disponibles en la base de datos** "
            f"para este ítem del local *{local_name}*"
        )
        photo_cols = st.columns(min(len(db_photos), 4))
        for i, p in enumerate(db_photos):
            with photo_cols[i % len(photo_cols)]:
                st.image(p["photo_data"], caption=p["photo_name"], use_container_width=True)

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

    has_any_photos = bool(db_photos) or bool(uploaded_files)

    analyze_btn = st.button(
        "🔍 Analizar con IA",
        type="primary",
        use_container_width=True,
        disabled=not has_any_photos or not api_key,
    )

    if not api_key:
        st.info("Ingresá tu OpenAI API Key en el panel izquierdo para empezar.")

    if analyze_btn and has_any_photos and api_key:
        photos_to_analyze = []

        if db_photos:
            for p in db_photos:
                photos_to_analyze.append({
                    "data": p["photo_data"],
                    "name": p["photo_name"],
                    "source": "db",
                })

        if uploaded_files:
            for f in uploaded_files:
                photos_to_analyze.append({
                    "data": f,
                    "name": f.name,
                    "source": "upload",
                })

        past_corrections = []
        if db.is_connected():
            try:
                past_corrections = db.get_corrections_for_item(criterion_id)
            except Exception:
                pass

        for photo_info in photos_to_analyze:
            with st.spinner(f"Analizando {photo_info['name']}..."):
                try:
                    if photo_info["source"] == "db":
                        img_file = io.BytesIO(photo_info["data"])
                        img_file.name = photo_info["name"]
                        img_file.type = "image/jpeg"
                        img_file.getvalue = lambda d=photo_info["data"]: d
                    else:
                        img_file = photo_info["data"]

                    result = analyze_photo(
                        api_key=api_key,
                        image_file=img_file,
                        criterion=selected_criterion,
                        model=model_choice,
                        corrections=past_corrections,
                    )

                    entry = {
                        "criterion": selected_criterion,
                        "result": result,
                        "filename": photo_info["name"],
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    st.session_state.results.append(entry)

                    if db.is_connected() and local_name:
                        try:
                            db.save_audit_result(
                                local=local_name,
                                fecha=datetime.now().strftime("%Y-%m"),
                                section=selected_criterion["section"],
                                item_id=selected_criterion["id"],
                                item_name=selected_criterion["name"],
                                result=result,
                                filename=photo_info["name"],
                                model=model_choice,
                            )
                        except Exception as e:
                            st.warning(f"No se pudo guardar el resultado en MongoDB: {e}")

                    _render_result(result, selected_criterion, len(st.session_state.results))

                except Exception as exc:
                    st.error(f"Error al analizar {photo_info['name']}: {exc}")

    if st.session_state.results:
        current_item_results = [
            (i, entry) for i, entry in enumerate(st.session_state.results)
            if entry["criterion"]["id"] == criterion_id
        ]
        other_results = [
            (i, entry) for i, entry in enumerate(st.session_state.results)
            if entry["criterion"]["id"] != criterion_id
        ]

        if current_item_results:
            st.divider()
            st.subheader(f"Resultado: {criterion_id}")

            if len(current_item_results) > 1:
                all_ai_statuses = [e["result"].get("status", "Observación") for _, e in current_item_results]
                consolidated = _worst_status(all_ai_statuses)
                counts = {s: all_ai_statuses.count(s) for s in set(all_ai_statuses)}
                counts_str = ", ".join(f"{s}: {c}" for s, c in counts.items())
                icon = STATUS_ICONS.get(consolidated, "")
                st.info(
                    f"**{len(current_item_results)} fotos analizadas** ({counts_str}) → "
                    f"**Status consolidado del ítem: {icon} {consolidated}** "
                    f"(se aplica el peor status)"
                )

            statuses_list = ["Conforme", "Observación", "No Conforme"]

            for orig_idx, entry in current_item_results:
                _render_result(entry["result"], entry["criterion"], orig_idx)

                ai_status = entry["result"].get("status", "Observación")
                default_idx = statuses_list.index(ai_status) if ai_status in statuses_list else 1

                st.caption("Si la IA se equivocó, ajustá el estado correcto:")
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.selectbox(
                        "Estado correcto",
                        statuses_list,
                        index=default_idx,
                        key=f"corr_status_{orig_idx}",
                    )
                with col_c2:
                    st.text_input(
                        "Nota del auditor (opcional)",
                        placeholder="Ej: Exhibidora fuera de lugar",
                        key=f"corr_notes_{orig_idx}",
                    )

            _final_statuses = {}
            for orig_idx, entry in current_item_results:
                ai_st = entry["result"].get("status", "Observación")
                corr_st = st.session_state.get(f"corr_status_{orig_idx}", ai_st)
                _final_statuses[orig_idx] = corr_st

            _any_non_conforme = any(s != "Conforme" for s in _final_statuses.values())
            _create_desvio_checked = False
            if _any_non_conforme and db.is_connected():
                _worst = "No Conforme" if "No Conforme" in _final_statuses.values() else "Observación"
                _create_desvio_checked = st.checkbox(
                    f"Crear desvío para {criterion_id} (estado: {_worst})",
                    value=True,
                    key=f"crear_desvio_{criterion_id}",
                )

            if st.button(
                "✅ Confirmar y siguiente",
                type="primary",
                use_container_width=True,
            ):
                fecha_now = datetime.now().strftime("%Y-%m")

                for orig_idx, entry in current_item_results:
                    ai_status = entry["result"].get("status", "Observación")
                    corrected = st.session_state.get(f"corr_status_{orig_idx}", ai_status)
                    notes = st.session_state.get(f"corr_notes_{orig_idx}", "")

                    if (corrected != ai_status or notes) and db.is_connected():
                        try:
                            db.save_correction(
                                item_id=entry["criterion"]["id"],
                                item_name=entry["criterion"]["name"],
                                ai_status=ai_status,
                                corrected_status=corrected,
                                ai_justificacion=entry["result"].get("justificacion", ""),
                                correction_notes=notes,
                                local=local_name,
                                fecha=fecha_now,
                            )
                        except Exception:
                            pass

                if _create_desvio_checked and db.is_connected():
                    try:
                        worst_status = "No Conforme" if "No Conforme" in _final_statuses.values() else "Observación"
                        nivel = "rojo" if worst_status == "No Conforme" else "amarillo"
                        prioridad = "alta" if worst_status == "No Conforme" else "media"
                        justif = current_item_results[0][1]["result"].get("justificacion", "")
                        db.create_desvio(
                            auditoria_fecha=fecha_now,
                            local=local_name,
                            seccion=selected_criterion["section"],
                            item_codigo=selected_criterion["id"],
                            item_descripcion=selected_criterion["name"][:120],
                            nivel=nivel,
                            ai_justificacion=justif,
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

        if other_results:
            st.divider()
            with st.expander(f"📋 Resultados anteriores ({len(other_results)})", expanded=False):
                for _, entry in reversed(other_results):
                    _render_result(entry["result"], entry["criterion"], _)

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
    "Los resultados del análisis de IA son orientativos y no reemplazan una auditoría formal."
)
