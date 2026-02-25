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
    SECTIONS,
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
No inventes lo que no se ve; solo evaluá lo visible en la imagen.\
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


# ── AI analysis ─────────────────────────────────────────────────────────
def _encode_image(uploaded_file) -> str:
    return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")


def analyze_photo(
    api_key: str,
    image_file,
    criterion: dict,
    model: str = "gpt-4o",
) -> dict:
    client = OpenAI(api_key=api_key)
    b64 = _encode_image(image_file)
    mime = image_file.type or "image/jpeg"

    user_prompt = (
        f"## Ítem a evaluar: {criterion['id']} — {criterion['name']}\n\n"
        f"**Criterios de CONFORME:**\n{criterion['conforme']}\n\n"
        f"**Criterios de OBSERVACIÓN:**\n{criterion['observacion']}\n\n"
        f"**Criterios de NO CONFORME:**\n{criterion['no_conforme']}\n\n"
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


def _build_report_df() -> pd.DataFrame:
    rows = []
    for r in st.session_state.results:
        rows.append(
            {
                "Ítem": r["criterion"]["id"],
                "Nombre": r["criterion"]["name"],
                "Sección": get_section_name(r["criterion"]["section"]),
                "Estado": r["result"]["status"],
                "Justificación": r["result"].get("justificacion", ""),
                "Detalles": "; ".join(r["result"].get("detalles_observados", [])),
                "Recomendaciones": "; ".join(r["result"].get("recomendaciones", [])),
                "Fecha": r.get("timestamp", ""),
            }
        )
    return pd.DataFrame(rows)


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

    local_name = st.text_input(
        "📍 Nombre del local",
        value=st.session_state.local_name,
        placeholder="Ej: Grido Centro Córdoba",
    )
    st.session_state.local_name = local_name

    st.divider()

    section = st.selectbox(
        "Sección a auditar",
        list(SECTIONS.keys()),
        format_func=lambda s: f"{s}. {SECTIONS[s]}",
    )

    section_criteria = get_criteria_by_section(section)
    criterion_id = st.selectbox(
        "Ítem específico",
        [c["id"] for c in section_criteria],
        format_func=lambda cid: f"{cid} — {get_criterion_by_id(cid)['name'][:60]}",
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
                    )

                    entry = {
                        "criterion": selected_criterion,
                        "result": result,
                        "filename": photo_info["name"],
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    st.session_state.results.append(entry)

                    _render_result(result, selected_criterion, len(st.session_state.results))

                except Exception as exc:
                    st.error(f"Error al analizar {photo_info['name']}: {exc}")

    if st.session_state.results:
        st.divider()
        st.subheader("Resultados de esta sesión")
        for i, entry in enumerate(reversed(st.session_state.results)):
            _render_result(entry["result"], entry["criterion"], i)

# ─── Tab: Reporte ───────────────────────────────────────────────────────
with tab_report:
    st.header("📊 Reporte de Auditoría")

    if not st.session_state.results:
        st.info("Todavía no hay resultados. Analizá al menos una foto en la pestaña Auditar.")
    else:
        st.markdown(
            f"**Local:** {st.session_state.local_name or '—'} · "
            f"**Fecha:** {st.session_state.audit_date} · "
            f"**Ítems evaluados:** {len(st.session_state.results)}"
        )
        st.divider()

        df = _build_report_df()

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

            total_items = len(CRITERIA)
            coverage = len(set(r["criterion"]["id"] for r in st.session_state.results))
            st.metric("Cobertura", f"{coverage}/{total_items} ítems")

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
