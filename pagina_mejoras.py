"""
Grido Audit Vision — Planes de Mejora.
Vista operativa (gestión de desvíos) y vista ejecutiva (dashboard + decisiones).
"""

from __future__ import annotations

import io
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from criteria import (
    ESTADOS_DESVIO,
    LOCALES,
    PRIORIDADES,
    ROLES_RESPONSABLE,
    SECTIONS,
    TIPOS_DESVIO,
)
import db

if not db.is_connected():
    st.warning(
        "MongoDB no está configurado. Planes de Mejora requiere conexión a la base de datos. "
        "Configurá `MONGODB_URI` en Settings > Secrets."
    )
    st.stop()

rol = st.session_state.get("rol", "operativo")


# ══════════════════════════════════════════════════════════════════════════
# VISTA OPERATIVA
# ══════════════════════════════════════════════════════════════════════════


def _render_vista_operativa():
    tab_bandeja, tab_plan, tab_control = st.tabs(
        ["Desvíos Activos", "Plan Semanal", "Control Semanal"]
    )

    local_filter = st.sidebar.selectbox("Filtrar local", ["Todos"] + LOCALES, key="mej_local")
    _local = None if local_filter == "Todos" else local_filter

    # ── Tab: Bandeja de Desvíos ──────────────────────────────────────────
    with tab_bandeja:
        st.header("Desvíos Activos")

        kpis = db.get_desvio_kpis(local=_local)
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Abiertos", kpis["abiertos"])
        k2.metric("% Cerrados en plazo (30d)", f"{kpis['pct_cerrados_en_plazo']}%")
        k3.metric("Reincidentes activos", kpis["reincidentes_activos"])
        k4.metric("Promedio cierre (90d)", f"{kpis['avg_dias_cierre']} días")

        st.divider()

        desvios = db.get_desvios(local=_local)
        activos = [d for d in desvios if d["estado"] in ("pendiente", "en_proceso")]

        if not activos:
            st.success("No hay desvíos activos.")
        else:
            for d in activos:
                did = d["_id"]
                color = "#e74c3c" if d["nivel"] == "rojo" else "#f39c12"
                reinc = " | REINCIDENTE" if d.get("reincidente") else ""
                st.markdown(
                    f"<div style='border-left:4px solid {color};padding:10px 14px;"
                    f"margin-bottom:12px;background:#fafafa;border-radius:4px;'>"
                    f"<strong>{d['item_codigo']} — {d.get('item_descripcion', '')[:80]}</strong>"
                    f" <small>({d['local']} · Sección {d['seccion']}{reinc})</small><br/>"
                    f"<small>Detectado: {_fmt_date(d.get('fecha_deteccion'))} · "
                    f"Tipo: {d.get('tipo_desvio', '—')} · Prioridad: {d.get('prioridad', '—')}</small>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                c1, c2, c3 = st.columns(3)
                with c1:
                    new_estado = st.selectbox(
                        "Estado",
                        ESTADOS_DESVIO,
                        index=ESTADOS_DESVIO.index(d["estado"]) if d["estado"] in ESTADOS_DESVIO else 0,
                        key=f"est_{did}",
                    )
                with c2:
                    responsables = db.get_responsables(local=d["local"])
                    resp_names = ["(sin asignar)"] + [r["nombre"] for r in responsables]
                    cur_resp = d.get("responsable", "")
                    resp_idx = resp_names.index(cur_resp) if cur_resp in resp_names else 0
                    new_resp = st.selectbox("Responsable", resp_names, index=resp_idx, key=f"resp_{did}")
                with c3:
                    cur_limit = d.get("fecha_limite")
                    if isinstance(cur_limit, datetime):
                        cur_limit = cur_limit.date()
                    new_limit = st.date_input(
                        "Fecha límite",
                        value=cur_limit or date.today() + timedelta(days=7),
                        key=f"lim_{did}",
                    )

                col_save, col_close = st.columns(2)
                with col_save:
                    if st.button("Guardar cambios", key=f"save_{did}"):
                        updates = {
                            "estado": new_estado,
                            "responsable": "" if new_resp == "(sin asignar)" else new_resp,
                            "fecha_limite": datetime.combine(new_limit, datetime.min.time()).replace(tzinfo=timezone.utc),
                        }
                        db.update_desvio(did, updates)
                        if new_estado == "cumplido":
                            db.close_desvio(did, "Cerrado desde bandeja")
                        st.success(f"Desvío {d['item_codigo']} actualizado.")
                        st.rerun()
                with col_close:
                    if d["estado"] != "cumplido":
                        comentario = st.text_input("Comentario cierre", key=f"com_{did}", placeholder="Describir resolución")
                        if st.button("Cerrar desvío", key=f"close_{did}"):
                            db.close_desvio(did, comentario or "Sin comentario")
                            if d.get("tipo_desvio") == "estructural":
                                try:
                                    db.create_decision(did, d["item_codigo"], d["local"], d.get("ai_justificacion", ""))
                                except Exception:
                                    pass
                            st.success(f"Desvío {d['item_codigo']} cerrado.")
                            st.rerun()

                st.divider()

    # ── Tab: Plan Semanal ────────────────────────────────────────────────
    with tab_plan:
        st.header("Plan de Mejora Semanal")

        plan_local = st.selectbox("Local", LOCALES, key="plan_local")
        desvios_plan = db.get_desvios(local=plan_local)
        activos_plan = [d for d in desvios_plan if d["estado"] in ("pendiente", "en_proceso")]

        activos_plan.sort(key=lambda d: (
            0 if d.get("reincidente") else 1,
            PRIORIDADES.index(d.get("prioridad", "baja")) if d.get("prioridad", "baja") in PRIORIDADES else 2,
        ))
        top10 = activos_plan[:10]

        if not top10:
            st.success("No hay desvíos activos para planificar.")
        else:
            st.markdown(f"**Top {len(top10)} desvíos activos** (reincidentes y alta prioridad primero):")
            selected_ids = []
            for d in top10:
                reinc = " (REINCIDENTE)" if d.get("reincidente") else ""
                checked = st.checkbox(
                    f"{d['item_codigo']} — {d.get('item_descripcion', '')[:60]}{reinc}",
                    value=True,
                    key=f"plan_{d['_id']}",
                )
                if checked:
                    selected_ids.append(d)

            if selected_ids and st.button("Generar plan semanal", type="primary", use_container_width=True):
                rows = []
                for d in selected_ids:
                    rows.append({
                        "Ítem": d["item_codigo"],
                        "Descripción": d.get("item_descripcion", "")[:80],
                        "Nivel": d.get("nivel", ""),
                        "Prioridad": d.get("prioridad", ""),
                        "Responsable": d.get("responsable", "Sin asignar"),
                        "Fecha límite": _fmt_date(d.get("fecha_limite")),
                    })
                df_plan = pd.DataFrame(rows)
                st.subheader(f"Plan semanal — {plan_local}")
                st.dataframe(df_plan, use_container_width=True, hide_index=True)

                csv = df_plan.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Descargar CSV",
                    data=csv,
                    file_name=f"plan_semanal_{plan_local}_{date.today()}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

    # ── Tab: Control Semanal ─────────────────────────────────────────────
    with tab_control:
        st.header("Control Semanal")

        por_vencer = db.get_desvios_por_vencer(local=_local, days=7)
        vencidos = [d for d in por_vencer if d.get("fecha_limite") and d["fecha_limite"] < datetime.now(timezone.utc)]
        proximos = [d for d in por_vencer if d.get("fecha_limite") and d["fecha_limite"] >= datetime.now(timezone.utc)]

        st.metric("Vencidos", len(vencidos))
        st.metric("Vencen en 7 días", len(proximos))

        if not por_vencer:
            st.success("No hay desvíos vencidos ni por vencer.")
        else:
            for d in por_vencer:
                vencido = d.get("fecha_limite") and d["fecha_limite"] < datetime.now(timezone.utc)
                icon = "🔴" if vencido else "🟡"
                st.markdown(
                    f"{icon} **{d['item_codigo']}** — {d.get('item_descripcion', '')[:60]} "
                    f"({d['local']}) · Límite: {_fmt_date(d.get('fecha_limite'))}"
                )

            if st.button("Revisión de miércoles", type="primary", use_container_width=True):
                cumplidos = 0
                pendientes = 0
                for d in por_vencer:
                    if d.get("fecha_limite") and d["fecha_limite"] < datetime.now(timezone.utc):
                        db.update_desvio(d["_id"], {"estado": "incumplido"})
                        pendientes += 1
                    else:
                        pendientes += 1

                st.info(f"Revisión completada. {pendientes} desvío(s) revisados.")
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════
# VISTA EJECUTIVA
# ══════════════════════════════════════════════════════════════════════════


def _render_vista_ejecutiva():
    tab_dash, tab_dec, tab_report = st.tabs(
        ["Dashboard", "Decisiones", "Reporte Mensual"]
    )

    local_filter = st.sidebar.selectbox("Filtrar local", ["Todos"] + LOCALES, key="ej_local")
    _local = None if local_filter == "Todos" else local_filter

    # ── Tab: Dashboard ───────────────────────────────────────────────────
    with tab_dash:
        st.header("Dashboard Ejecutivo")

        kpis = db.get_desvio_kpis(local=_local)
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Desvíos abiertos", kpis["abiertos"])
        k2.metric("% En plazo (30d)", f"{kpis['pct_cerrados_en_plazo']}%")
        k3.metric("Reincidentes", kpis["reincidentes_activos"])
        k4.metric("Días promedio cierre", kpis["avg_dias_cierre"])

        st.divider()

        for loc in (LOCALES if not _local else [_local]):
            scores_data = db.get_monthly_scores(loc, months=6)
            if scores_data:
                st.subheader(f"Evolución — {loc}")

                fechas = [s["fecha"] for s in scores_data]
                globals_ = [s.get("score_global", 0) for s in scores_data]

                df_trend = pd.DataFrame({"Período": fechas, "Score Global": globals_})
                st.line_chart(df_trend.set_index("Período"))

                rows = []
                for s in scores_data:
                    row = {"Período": s["fecha"]}
                    for sec_key, sec_name in SECTIONS.items():
                        row[f"{sec_key}. {sec_name[:20]}"] = s.get("scores", {}).get(sec_key, 0)
                    row["Global"] = s.get("score_global", 0)
                    rows.append(row)
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Top 5 ítems reincidentes")
        reincidentes = db.get_top_reincidentes(local=_local, limit=5)
        if reincidentes:
            for r in reincidentes:
                st.markdown(
                    f"**{r['item_codigo']}** — {r.get('item_descripcion', '')[:60]} "
                    f"({r['local']}) · {r['count']} veces"
                )
        else:
            st.success("No hay ítems reincidentes.")

        st.divider()
        st.subheader("Desvíos estructurales pendientes")
        estructurales = [
            d for d in db.get_desvios(local=_local)
            if d.get("tipo_desvio") == "estructural" and d["estado"] in ("pendiente", "en_proceso")
        ]
        if estructurales:
            for d in estructurales:
                st.markdown(
                    f"**{d['item_codigo']}** — {d.get('item_descripcion', '')[:60]} "
                    f"({d['local']}) · Detectado: {_fmt_date(d.get('fecha_deteccion'))}"
                )
        else:
            st.success("No hay desvíos estructurales pendientes.")

    # ── Tab: Decisiones ──────────────────────────────────────────────────
    with tab_dec:
        st.header("Panel de Decisiones")
        st.caption("Desvíos estructurales que requieren decisión de la dirección.")

        decisiones = db.get_decisiones_pendientes(local=_local)

        if not decisiones:
            estructurales_sin_dec = [
                d for d in db.get_desvios(local=_local)
                if d.get("tipo_desvio") == "estructural"
                and d["estado"] in ("pendiente", "en_proceso")
            ]
            if estructurales_sin_dec:
                st.info("Hay desvíos estructurales sin decisión creada. Se crean automáticamente al cerrar un desvío estructural.")
                for d in estructurales_sin_dec:
                    if st.button(f"Crear decisión para {d['item_codigo']}", key=f"creat_dec_{d['_id']}"):
                        db.create_decision(d["_id"], d["item_codigo"], d["local"], d.get("ai_justificacion", ""))
                        st.rerun()
            else:
                st.success("No hay decisiones pendientes.")
        else:
            for dec in decisiones:
                dec_id = dec["_id"]
                st.markdown(f"### {dec['item_codigo']} — {dec['local']}")

                impacto = st.text_area(
                    "Impacto",
                    value=dec.get("impacto", ""),
                    key=f"imp_{dec_id}",
                )
                propuesta = st.text_area(
                    "Propuesta de la dirección",
                    value=dec.get("propuesta", ""),
                    key=f"prop_{dec_id}",
                )
                estado_dec = st.selectbox(
                    "Estado decisión",
                    ["pendiente", "aprobado", "descartado"],
                    index=["pendiente", "aprobado", "descartado"].index(dec.get("estado_decision", "pendiente")),
                    key=f"edec_{dec_id}",
                )
                if st.button("Guardar decisión", key=f"sdec_{dec_id}"):
                    db.update_decision(dec_id, {
                        "impacto": impacto,
                        "propuesta": propuesta,
                        "estado_decision": estado_dec,
                    })
                    st.success(f"Decisión actualizada para {dec['item_codigo']}.")
                    st.rerun()

                st.divider()

    # ── Tab: Reporte Mensual ─────────────────────────────────────────────
    with tab_report:
        st.header("Reporte Mensual")

        report_local = st.selectbox("Local", LOCALES, key="rep_local")
        meses_disponibles = [a["fecha"] for a in db.get_auditorias_list(local=report_local, limit=12)]

        if not meses_disponibles:
            st.info("No hay auditorías registradas para generar un reporte.")
        else:
            mes_sel = st.selectbox("Mes", meses_disponibles, key="rep_mes")
            aud = db.get_auditoria(report_local, mes_sel)

            if aud:
                st.subheader(f"Resumen — {report_local} — {mes_sel}")
                st.metric("Score global", f"{aud.get('score_global', 0)}%")

                scores = aud.get("scores", {})
                for sec_key, sec_name in SECTIONS.items():
                    score = scores.get(sec_key, 0)
                    st.markdown(f"**{sec_key}. {sec_name}** — {score}%")
                    st.progress(score / 100)

                st.divider()
                st.subheader("Desvíos del período")
                desvios_mes = [
                    d for d in db.get_desvios(local=report_local)
                    if d.get("auditoria_fecha") == mes_sel
                ]
                if desvios_mes:
                    rows = []
                    for d in desvios_mes:
                        rows.append({
                            "Ítem": d["item_codigo"],
                            "Descripción": d.get("item_descripcion", "")[:60],
                            "Nivel": d.get("nivel", ""),
                            "Estado": d.get("estado", ""),
                            "Tipo": d.get("tipo_desvio", ""),
                            "Reincidente": "Sí" if d.get("reincidente") else "No",
                        })
                    df_desv = pd.DataFrame(rows)
                    st.dataframe(df_desv, use_container_width=True, hide_index=True)

                    csv = df_desv.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Descargar reporte CSV",
                        data=csv,
                        file_name=f"reporte_{report_local}_{mes_sel}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
                else:
                    st.success("No se registraron desvíos en este período.")

                st.divider()
                st.subheader("Ítems reincidentes")
                reinc = db.get_top_reincidentes(local=report_local, limit=5)
                if reinc:
                    for r in reinc:
                        st.markdown(f"- **{r['item_codigo']}**: {r['count']} veces detectado")
                else:
                    st.success("Sin reincidencias.")

                all_scores = db.get_monthly_scores(report_local, months=2)
                if len(all_scores) >= 2:
                    prev = all_scores[-2].get("score_global", 0)
                    curr = all_scores[-1].get("score_global", 0)
                    diff = curr - prev
                    if diff > 0:
                        st.success(f"Mejora de {diff} puntos respecto al período anterior.")
                    elif diff < 0:
                        st.warning(f"Caída de {abs(diff)} puntos respecto al período anterior.")
                    else:
                        st.info("Score sin cambios respecto al período anterior.")
            else:
                st.info("No se encontró auditoría para este período.")


# ══════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════


def _fmt_date(dt) -> str:
    if dt is None:
        return "—"
    if isinstance(dt, datetime):
        return dt.strftime("%d/%m/%Y")
    if isinstance(dt, date):
        return dt.strftime("%d/%m/%Y")
    return str(dt)


# ══════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════

st.markdown("## 📊 Planes de Mejora")

if rol == "operativo":
    st.caption("Vista operativa — Gestión de desvíos y planes de mejora")
    _render_vista_operativa()
elif rol == "ejecutivo":
    st.caption("Vista ejecutiva — Dashboard, decisiones y reportes")
    _render_vista_ejecutiva()
