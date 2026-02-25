"""
Grido Audit Vision — Historial y seguimiento de auditorías.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from criteria import CRITERIA, SECTIONS, get_section_name
import db

if not db.is_connected():
    st.warning(
        "MongoDB no está configurado. El historial requiere conexión a la base de datos. "
        "Configurá `MONGODB_URI` en Settings > Secrets."
    )
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────
tab_overview, tab_detail, tab_trends, tab_admin = st.tabs(
    ["Resumen", "Detalle por auditoría", "Tendencias", "Admin / Stats"]
)

history = db.get_audit_history()

# ── Tab: Resumen ──────────────────────────────────────────────────────────
with tab_overview:
    st.header("Resumen de auditorías")

    if not history:
        st.info("Todavía no hay auditorías registradas.")
    else:
        df_hist = pd.DataFrame(history)
        df_hist = df_hist.rename(columns={
            "local": "Local",
            "fecha": "Período",
            "total": "Ítems",
            "conformes": "Conformes",
            "observaciones": "Observaciones",
            "no_conformes": "No Conformes",
            "pct_conforme": "% Conforme",
        })
        df_hist = df_hist.drop(columns=["last_analyzed"], errors="ignore")

        st.dataframe(
            df_hist,
            use_container_width=True,
            hide_index=True,
            column_config={
                "% Conforme": st.column_config.ProgressColumn(
                    min_value=0, max_value=100, format="%d%%"
                ),
            },
        )

        st.divider()

        locales = df_hist["Local"].unique().tolist()
        if len(locales) > 1:
            st.subheader("Comparativa por local")
            compare_df = (
                df_hist.groupby("Local")
                .agg({"Ítems": "sum", "Conformes": "sum", "No Conformes": "sum"})
                .reset_index()
            )
            compare_df["% Conforme"] = (
                compare_df["Conformes"] / compare_df["Ítems"] * 100
            ).round(0)
            st.dataframe(compare_df, use_container_width=True, hide_index=True)


# ── Tab: Detalle ──────────────────────────────────────────────────────────
with tab_detail:
    st.header("Detalle por auditoría")

    if not history:
        st.info("No hay auditorías registradas.")
    else:
        options = [f"{h['local']} — {h['fecha']}" for h in history]
        selected = st.selectbox("Seleccionar auditoría", options, key="hist_detail_sel")
        idx = options.index(selected)
        sel = history[idx]

        results = db.get_audit_results(sel["local"], sel["fecha"])
        if not results:
            st.info("No se encontraron resultados para esta auditoría.")
        else:
            rows = []
            for r in results:
                rows.append({
                    "Sección": get_section_name(r.get("section", "")),
                    "Ítem": r["item_id"],
                    "Nombre": r.get("item_name", ""),
                    "Estado": r["status"],
                    "Justificación": r.get("justificacion", ""),
                    "Detalles": "; ".join(r.get("detalles_observados", [])),
                    "Recomendaciones": "; ".join(r.get("recomendaciones", [])),
                })
            df_detail = pd.DataFrame(rows)

            status_counts = df_detail["Estado"].value_counts()
            cols = st.columns(3)
            for i, status_val in enumerate(["Conforme", "Observación", "No Conforme"]):
                count = status_counts.get(status_val, 0)
                pct = round(count / len(df_detail) * 100) if len(df_detail) else 0
                cols[i].metric(
                    f"{'✅' if status_val == 'Conforme' else '⚠️' if status_val == 'Observación' else '❌'} {status_val}",
                    f"{count} ({pct}%)",
                )

            st.divider()

            for sec_key, sec_name in SECTIONS.items():
                sec_df = df_detail[df_detail["Sección"] == sec_name]
                if sec_df.empty:
                    continue
                with st.expander(f"**{sec_key}. {sec_name}** — {len(sec_df)} ítems"):
                    for _, row in sec_df.iterrows():
                        status = row["Estado"]
                        color = {"Conforme": "#2ecc71", "Observación": "#f39c12", "No Conforme": "#e74c3c"}.get(status, "#95a5a6")
                        icon = {"Conforme": "✅", "Observación": "⚠️", "No Conforme": "❌"}.get(status, "❔")
                        st.markdown(
                            f"<div style='border-left:4px solid {color};padding:8px 12px;"
                            f"margin-bottom:8px;background:#fafafa;border-radius:4px;'>"
                            f"<strong>{row['Ítem']} — {row['Nombre']}</strong> "
                            f"<span style='background:{color};color:white;padding:2px 8px;"
                            f"border-radius:8px;font-size:0.85rem;'>{icon} {status}</span><br/>"
                            f"<small>{row['Justificación']}</small>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )


# ── Tab: Tendencias ───────────────────────────────────────────────────────
with tab_trends:
    st.header("Tendencias y puntos recurrentes")

    if not history:
        st.info("No hay auditorías registradas.")
    else:
        locales = list({h["local"] for h in history})
        local_sel = st.selectbox("Local", locales, key="trend_local")

        st.subheader("Evolución de conformidad")
        local_history = [h for h in history if h["local"] == local_sel]
        local_history.sort(key=lambda h: h["fecha"])

        if len(local_history) >= 2:
            df_trend = pd.DataFrame(local_history)[["fecha", "pct_conforme", "conformes", "no_conformes", "total"]]
            df_trend = df_trend.rename(columns={
                "fecha": "Período",
                "pct_conforme": "% Conforme",
                "conformes": "Conformes",
                "no_conformes": "No Conformes",
                "total": "Total",
            })
            st.line_chart(df_trend.set_index("Período")["% Conforme"])
            st.dataframe(df_trend, use_container_width=True, hide_index=True)
        elif len(local_history) == 1:
            h = local_history[0]
            st.metric("Conformidad", f"{h['pct_conforme']}%", help=f"Período: {h['fecha']}")
            st.caption("Se necesitan al menos 2 auditorías para mostrar la tendencia.")
        else:
            st.info("No hay datos para este local.")

        st.divider()
        st.subheader("Ítems con fallas recurrentes")
        failures = db.get_recurring_failures(local_sel, min_count=2)
        if failures:
            for f in failures:
                st.markdown(
                    f"**{f['item_id']} — {f['item_name']}** "
                    f"| {f['fail_count']} fallas en períodos: {', '.join(f['fechas'])}"
                )
        else:
            st.success("No se detectaron ítems con fallas recurrentes (2+).")

        st.divider()
        st.subheader("Evolución por ítem")
        all_items = [(c["id"], c["name"]) for c in CRITERIA]
        item_sel = st.selectbox(
            "Seleccionar ítem",
            [f"{cid} — {cname[:60]}" for cid, cname in all_items],
            key="trend_item",
        )
        item_id = item_sel.split(" — ")[0]
        evolution = db.get_item_evolution(local_sel, item_id)
        if evolution:
            df_evo = pd.DataFrame(evolution)
            df_evo = df_evo.rename(columns={
                "fecha": "Período",
                "status": "Estado",
                "justificacion": "Justificación",
            })
            df_evo = df_evo.drop(columns=["analyzed_at"], errors="ignore")
            st.dataframe(df_evo, use_container_width=True, hide_index=True)
        else:
            st.info(f"No hay datos para {item_id} en {local_sel}.")


# ── Tab: Admin ────────────────────────────────────────────────────────────
with tab_admin:
    st.header("Administración y estadísticas")

    try:
        stats = db.get_stats()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fotos almacenadas", stats["photo_count"])
        c2.metric("Espacio fotos", f"{stats['photos_size_mb']} MB")
        c3.metric("Resultados de auditoría", stats["result_count"])
        c4.metric("Auditorías distintas", stats["distinct_audits"])

    except Exception as e:
        st.error(f"Error al obtener estadísticas: {e}")

    st.divider()
    st.subheader("Limpieza de fotos antiguas")
    st.markdown(
        "Las fotos ocupan espacio significativo. Podés eliminar las que tienen más de 6 meses. "
        "Los **reportes de auditoría se mantienen** indefinidamente."
    )

    months = st.number_input("Eliminar fotos anteriores a (meses)", min_value=1, max_value=24, value=6)

    if st.button("Limpiar fotos antiguas", type="primary"):
        with st.spinner("Eliminando fotos antiguas..."):
            try:
                deleted = db.cleanup_old_photos(months=months)
                if deleted > 0:
                    st.success(f"Se eliminaron {deleted} fotos anteriores a {months} meses.")
                else:
                    st.info("No hay fotos anteriores al período indicado.")
            except Exception as e:
                st.error(f"Error al limpiar: {e}")
