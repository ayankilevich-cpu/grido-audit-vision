"""
Grido Audit Vision — Capa de datos (MongoDB Atlas).

Colecciones:
  photos         — fotos comprimidas (se purgan a los 6 meses)
  audit_results  — resultados del análisis IA (se mantienen indefinidamente)
  corrections    — correcciones del auditor humano (retroalimentación para mejorar la IA)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import streamlit as st


def _get_uri() -> str | None:
    try:
        uri = st.secrets.get("MONGODB_URI", "")
        return uri if uri else None
    except Exception:
        return None


@st.cache_resource
def _connect(uri: str):
    from pymongo import MongoClient

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    return client


def is_connected() -> bool:
    uri = _get_uri()
    if not uri:
        return False
    try:
        _connect(uri)
        return True
    except Exception:
        return False


def _col():
    """Return the photos collection."""
    uri = _get_uri()
    if not uri:
        raise RuntimeError("MONGODB_URI not configured")
    client = _connect(uri)
    db = client["grido_audit"]
    col = db["photos"]
    col.create_index([("local", 1), ("fecha", 1), ("item_id", 1)])
    return col


# ── CRUD ──────────────────────────────────────────────────────────────────


def save_photo(
    local: str,
    fecha: str,
    section: str,
    item_id: str,
    photo_data: bytes,
    photo_name: str,
) -> str:
    """Save a compressed photo. Returns the inserted document ID as string."""
    doc = {
        "local": local,
        "fecha": fecha,
        "section": section,
        "item_id": item_id,
        "photo_name": photo_name,
        "photo_data": photo_data,
        "size_bytes": len(photo_data),
        "created_at": datetime.now(timezone.utc),
    }
    result = _col().insert_one(doc)
    return str(result.inserted_id)


def get_photos_for_item(
    local: str, fecha: str, item_id: str
) -> list[dict[str, Any]]:
    """Return photos for a specific item (with binary data)."""
    cursor = _col().find(
        {"local": local, "fecha": fecha, "item_id": item_id},
        {"photo_data": 1, "photo_name": 1, "_id": 1},
    ).sort("photo_name", 1)
    return list(cursor)


def get_photo_counts(local: str, fecha: str) -> dict[str, int]:
    """Return {item_id: photo_count} for progress tracking."""
    pipeline = [
        {"$match": {"local": local, "fecha": fecha}},
        {"$group": {"_id": "$item_id", "count": {"$sum": 1}}},
    ]
    result = _col().aggregate(pipeline)
    return {doc["_id"]: doc["count"] for doc in result}


def get_total_size(local: str, fecha: str) -> int:
    """Return total size in bytes for an audit."""
    pipeline = [
        {"$match": {"local": local, "fecha": fecha}},
        {"$group": {"_id": None, "total": {"$sum": "$size_bytes"}}},
    ]
    result = list(_col().aggregate(pipeline))
    return result[0]["total"] if result else 0


def delete_photo(photo_id: str) -> bool:
    """Delete a photo by its MongoDB _id."""
    from bson import ObjectId

    result = _col().delete_one({"_id": ObjectId(photo_id)})
    return result.deleted_count > 0


def get_all_photos(local: str, fecha: str) -> list[dict[str, Any]]:
    """Return all photos for an audit (for ZIP generation)."""
    cursor = _col().find(
        {"local": local, "fecha": fecha},
        {"photo_data": 1, "photo_name": 1, "section": 1, "item_id": 1, "_id": 0},
    ).sort([("section", 1), ("item_id", 1), ("photo_name", 1)])
    return list(cursor)


def next_photo_name(local: str, fecha: str, item_id: str) -> str:
    """Generate the next sequential photo name for an item."""
    code = item_id.replace(".", "")
    count = _col().count_documents(
        {"local": local, "fecha": fecha, "item_id": item_id}
    )
    return f"{code}_{count + 1:03d}.jpg"


def get_audits() -> list[dict[str, str]]:
    """Return list of distinct (local, fecha) combinations from photos."""
    pipeline = [
        {"$group": {"_id": {"local": "$local", "fecha": "$fecha"}}},
        {"$sort": {"_id.fecha": -1, "_id.local": 1}},
    ]
    result = _col().aggregate(pipeline)
    return [{"local": doc["_id"]["local"], "fecha": doc["_id"]["fecha"]} for doc in result]


# ── Colección: audit_results ──────────────────────────────────────────────


def _results_col():
    """Return the audit_results collection."""
    uri = _get_uri()
    if not uri:
        raise RuntimeError("MONGODB_URI not configured")
    client = _connect(uri)
    db = client["grido_audit"]
    col = db["audit_results"]
    col.create_index([("local", 1), ("fecha", 1), ("item_id", 1)])
    return col


def save_audit_result(
    local: str,
    fecha: str,
    section: str,
    item_id: str,
    item_name: str,
    result: dict,
    filename: str,
    model: str,
) -> str:
    """Persist an AI audit result. Returns inserted ID."""
    doc = {
        "local": local,
        "fecha": fecha,
        "section": section,
        "item_id": item_id,
        "item_name": item_name,
        "status": result.get("status", "Observación"),
        "justificacion": result.get("justificacion", ""),
        "detalles_observados": result.get("detalles_observados", []),
        "recomendaciones": result.get("recomendaciones", []),
        "filename": filename,
        "model": model,
        "analyzed_at": datetime.now(timezone.utc),
    }
    r = _results_col().insert_one(doc)
    return str(r.inserted_id)


def get_audit_results(local: str, fecha: str) -> list[dict[str, Any]]:
    """Return all audit results for a given local+fecha."""
    cursor = _results_col().find(
        {"local": local, "fecha": fecha},
        {"_id": 0},
    ).sort([("section", 1), ("item_id", 1), ("analyzed_at", 1)])
    return list(cursor)


def get_audit_history() -> list[dict[str, Any]]:
    """Return summary of past audits: local, fecha, counts, conformity %."""
    pipeline = [
        {
            "$group": {
                "_id": {"local": "$local", "fecha": "$fecha"},
                "total": {"$sum": 1},
                "conformes": {
                    "$sum": {"$cond": [{"$eq": ["$status", "Conforme"]}, 1, 0]}
                },
                "observaciones": {
                    "$sum": {"$cond": [{"$eq": ["$status", "Observación"]}, 1, 0]}
                },
                "no_conformes": {
                    "$sum": {"$cond": [{"$eq": ["$status", "No Conforme"]}, 1, 0]}
                },
                "last_analyzed": {"$max": "$analyzed_at"},
            }
        },
        {"$sort": {"_id.fecha": -1, "_id.local": 1}},
    ]
    result = _results_col().aggregate(pipeline)
    return [
        {
            "local": doc["_id"]["local"],
            "fecha": doc["_id"]["fecha"],
            "total": doc["total"],
            "conformes": doc["conformes"],
            "observaciones": doc["observaciones"],
            "no_conformes": doc["no_conformes"],
            "pct_conforme": round(doc["conformes"] / doc["total"] * 100) if doc["total"] else 0,
            "last_analyzed": doc["last_analyzed"],
        }
        for doc in result
    ]


def get_item_evolution(local: str, item_id: str) -> list[dict[str, Any]]:
    """Return status history of a single item across audits."""
    cursor = _results_col().find(
        {"local": local, "item_id": item_id},
        {"_id": 0, "fecha": 1, "status": 1, "justificacion": 1, "analyzed_at": 1},
    ).sort("fecha", 1)
    return list(cursor)


def get_recurring_failures(local: str, min_count: int = 2) -> list[dict[str, Any]]:
    """Items that were No Conforme or Observación in multiple audits."""
    pipeline = [
        {"$match": {"local": local, "status": {"$ne": "Conforme"}}},
        {
            "$group": {
                "_id": {"item_id": "$item_id", "item_name": "$item_name"},
                "fail_count": {"$sum": 1},
                "fechas": {"$addToSet": "$fecha"},
                "statuses": {"$push": "$status"},
            }
        },
        {"$match": {"fail_count": {"$gte": min_count}}},
        {"$sort": {"fail_count": -1}},
    ]
    result = _results_col().aggregate(pipeline)
    return [
        {
            "item_id": doc["_id"]["item_id"],
            "item_name": doc["_id"]["item_name"],
            "fail_count": doc["fail_count"],
            "fechas": sorted(doc["fechas"]),
        }
        for doc in result
    ]


def get_stats() -> dict[str, Any]:
    """Return database stats for the admin panel."""
    photos_col = _col()
    results_col = _results_col()

    photo_count = photos_col.count_documents({})
    result_count = results_col.count_documents({})

    size_pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$size_bytes"}}}
    ]
    size_result = list(photos_col.aggregate(size_pipeline))
    photos_size = size_result[0]["total"] if size_result else 0

    distinct_audits = len(list(results_col.aggregate([
        {"$group": {"_id": {"local": "$local", "fecha": "$fecha"}}},
    ])))

    return {
        "photo_count": photo_count,
        "result_count": result_count,
        "photos_size_mb": round(photos_size / (1024 * 1024), 1),
        "distinct_audits": distinct_audits,
    }


def cleanup_old_photos(months: int = 6) -> int:
    """Delete photos older than `months`. Returns count of deleted documents."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)
    result = _col().delete_many({"created_at": {"$lt": cutoff}})
    return result.deleted_count


# ── Colección: corrections (retroalimentación) ───────────────────────────


def _corrections_col():
    """Return the corrections collection."""
    uri = _get_uri()
    if not uri:
        raise RuntimeError("MONGODB_URI not configured")
    client = _connect(uri)
    db = client["grido_audit"]
    col = db["corrections"]
    col.create_index([("item_id", 1), ("created_at", -1)])
    return col


def save_correction(
    item_id: str,
    item_name: str,
    ai_status: str,
    corrected_status: str,
    ai_justificacion: str,
    correction_notes: str,
    local: str = "",
    fecha: str = "",
) -> str:
    """Save an auditor's correction of the AI result."""
    doc = {
        "item_id": item_id,
        "item_name": item_name,
        "ai_status": ai_status,
        "corrected_status": corrected_status,
        "ai_justificacion": ai_justificacion,
        "correction_notes": correction_notes,
        "local": local,
        "fecha": fecha,
        "created_at": datetime.now(timezone.utc),
    }
    r = _corrections_col().insert_one(doc)
    return str(r.inserted_id)


def get_corrections_for_item(item_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return recent corrections for a specific item (for few-shot prompting)."""
    cursor = (
        _corrections_col()
        .find(
            {"item_id": item_id},
            {"_id": 0, "ai_status": 1, "corrected_status": 1,
             "ai_justificacion": 1, "correction_notes": 1},
        )
        .sort("created_at", -1)
        .limit(limit)
    )
    return list(cursor)


def get_all_corrections(limit: int = 50) -> list[dict[str, Any]]:
    """Return recent corrections across all items."""
    cursor = (
        _corrections_col()
        .find({}, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit)
    )
    return list(cursor)


# ══════════════════════════════════════════════════════════════════════════
# Colección: auditorias
# ══════════════════════════════════════════════════════════════════════════


def _auditorias_col():
    uri = _get_uri()
    if not uri:
        raise RuntimeError("MONGODB_URI not configured")
    client = _connect(uri)
    col = client["grido_audit"]["auditorias"]
    col.create_index([("local", 1), ("fecha", 1)], unique=True)
    return col


def calculate_section_scores(local: str, fecha: str) -> dict[str, int]:
    """Compute score 0-100 per section from audit_results."""
    results = get_audit_results(local, fecha)
    section_points: dict[str, list[int]] = {}
    score_map = {"Conforme": 100, "Observación": 50, "No Conforme": 0}
    for r in results:
        sec = r.get("section", "")
        pts = score_map.get(r.get("status", ""), 50)
        section_points.setdefault(sec, []).append(pts)
    return {
        sec: round(sum(pts) / len(pts)) if pts else 0
        for sec, pts in section_points.items()
    }


def upsert_auditoria(
    local: str,
    fecha: str,
    tipo: str,
    created_by: str = "operativo",
    franquiciado_id: str = "grido_default",
) -> None:
    scores = calculate_section_scores(local, fecha)
    all_pts = [v for v in scores.values() if v is not None]
    score_global = round(sum(all_pts) / len(all_pts)) if all_pts else 0
    results = get_audit_results(local, fecha)
    now = datetime.now(timezone.utc)
    _auditorias_col().update_one(
        {"local": local, "fecha": fecha},
        {
            "$set": {
                "tipo_auditoria": tipo,
                "scores": scores,
                "score_global": score_global,
                "items_evaluados": len(results),
                "created_by": created_by,
                "franquiciado_id": franquiciado_id,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )


def get_auditoria(local: str, fecha: str) -> dict[str, Any] | None:
    return _auditorias_col().find_one(
        {"local": local, "fecha": fecha}, {"_id": 0}
    )


def get_auditorias_list(local: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    filt: dict = {}
    if local:
        filt["local"] = local
    cursor = (
        _auditorias_col()
        .find(filt, {"_id": 0})
        .sort("fecha", -1)
        .limit(limit)
    )
    return list(cursor)


def get_monthly_scores(local: str, months: int = 6) -> list[dict[str, Any]]:
    cursor = (
        _auditorias_col()
        .find(
            {"local": local},
            {"_id": 0, "fecha": 1, "scores": 1, "score_global": 1},
        )
        .sort("fecha", -1)
        .limit(months)
    )
    return list(reversed(list(cursor)))


# ══════════════════════════════════════════════════════════════════════════
# Colección: desvios
# ══════════════════════════════════════════════════════════════════════════


def _desvios_col():
    uri = _get_uri()
    if not uri:
        raise RuntimeError("MONGODB_URI not configured")
    client = _connect(uri)
    col = client["grido_audit"]["desvios"]
    col.create_index([("local", 1), ("estado", 1)])
    col.create_index([("item_codigo", 1), ("fecha_deteccion", -1)])
    return col


def _check_recurrence(local: str, item_codigo: str, days: int = 60) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return _desvios_col().count_documents({
        "local": local,
        "item_codigo": item_codigo,
        "fecha_deteccion": {"$gte": cutoff},
    })


def create_desvio(
    auditoria_fecha: str,
    local: str,
    seccion: str,
    item_codigo: str,
    item_descripcion: str,
    nivel: str,
    ai_justificacion: str = "",
    prioridad: str = "media",
    franquiciado_id: str = "grido_default",
) -> str:
    veces = _check_recurrence(local, item_codigo) + 1
    tipo = "estructural" if veces >= 3 else "operativo"
    doc = {
        "auditoria_fecha": auditoria_fecha,
        "fecha_deteccion": datetime.now(timezone.utc),
        "local": local,
        "seccion": seccion,
        "item_codigo": item_codigo,
        "item_descripcion": item_descripcion,
        "nivel": nivel,
        "tipo_desvio": tipo,
        "responsable": "",
        "fecha_limite": None,
        "estado": "pendiente",
        "fecha_cierre": None,
        "comentario_cierre": None,
        "reincidente": veces > 1,
        "veces_detectado_60d": veces,
        "prioridad": prioridad,
        "ai_justificacion": ai_justificacion,
        "franquiciado_id": franquiciado_id,
        "created_at": datetime.now(timezone.utc),
    }
    r = _desvios_col().insert_one(doc)
    return str(r.inserted_id)


def get_desvios(
    local: str | None = None,
    estado: str | None = None,
    seccion: str | None = None,
) -> list[dict[str, Any]]:
    filt: dict = {}
    if local:
        filt["local"] = local
    if estado:
        filt["estado"] = estado
    if seccion:
        filt["seccion"] = seccion
    cursor = (
        _desvios_col()
        .find(filt)
        .sort([("prioridad", 1), ("fecha_deteccion", -1)])
    )
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results


def update_desvio(desvio_id: str, updates: dict) -> bool:
    from bson import ObjectId
    updates["updated_at"] = datetime.now(timezone.utc)
    r = _desvios_col().update_one(
        {"_id": ObjectId(desvio_id)}, {"$set": updates}
    )
    return r.modified_count > 0


def close_desvio(desvio_id: str, comentario: str) -> bool:
    return update_desvio(desvio_id, {
        "estado": "cumplido",
        "fecha_cierre": datetime.now(timezone.utc),
        "comentario_cierre": comentario,
    })


def get_desvio_kpis(local: str | None = None, days: int = 30) -> dict[str, Any]:
    filt: dict = {}
    if local:
        filt["local"] = local
    col = _desvios_col()

    abiertos = col.count_documents({**filt, "estado": {"$in": ["pendiente", "en_proceso"]}})
    reincidentes = col.count_documents({**filt, "estado": {"$in": ["pendiente", "en_proceso"]}, "reincidente": True})

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cerrados_periodo = list(col.find({
        **filt,
        "estado": "cumplido",
        "fecha_cierre": {"$gte": cutoff},
    }))
    en_plazo = sum(
        1 for d in cerrados_periodo
        if d.get("fecha_limite") and d["fecha_cierre"] <= d["fecha_limite"]
    )
    pct_en_plazo = round(en_plazo / len(cerrados_periodo) * 100) if cerrados_periodo else 0

    cutoff_90 = datetime.now(timezone.utc) - timedelta(days=90)
    cerrados_90 = list(col.find({
        **filt,
        "estado": "cumplido",
        "fecha_cierre": {"$gte": cutoff_90},
    }))
    tiempos = [
        (d["fecha_cierre"] - d["fecha_deteccion"]).days
        for d in cerrados_90
        if d.get("fecha_cierre") and d.get("fecha_deteccion")
    ]
    avg_cierre = round(sum(tiempos) / len(tiempos)) if tiempos else 0

    return {
        "abiertos": abiertos,
        "reincidentes_activos": reincidentes,
        "pct_cerrados_en_plazo": pct_en_plazo,
        "avg_dias_cierre": avg_cierre,
    }


def get_top_reincidentes(local: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    match: dict = {"reincidente": True}
    if local:
        match["local"] = local
    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {"item_codigo": "$item_codigo", "item_descripcion": "$item_descripcion", "local": "$local"},
            "count": {"$sum": 1},
            "ultimo": {"$max": "$fecha_deteccion"},
        }},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    return [
        {
            "item_codigo": d["_id"]["item_codigo"],
            "item_descripcion": d["_id"]["item_descripcion"],
            "local": d["_id"]["local"],
            "count": d["count"],
            "ultimo": d["ultimo"],
        }
        for d in _desvios_col().aggregate(pipeline)
    ]


def get_desvios_por_vencer(local: str | None = None, days: int = 7) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    limit_date = now + timedelta(days=days)
    filt: dict = {
        "estado": {"$in": ["pendiente", "en_proceso"]},
        "fecha_limite": {"$ne": None, "$lte": limit_date},
    }
    if local:
        filt["local"] = local
    cursor = _desvios_col().find(filt).sort("fecha_limite", 1)
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results


# ══════════════════════════════════════════════════════════════════════════
# Colección: responsables
# ══════════════════════════════════════════════════════════════════════════


def _responsables_col():
    uri = _get_uri()
    if not uri:
        raise RuntimeError("MONGODB_URI not configured")
    client = _connect(uri)
    return client["grido_audit"]["responsables"]


def get_responsables(local: str | None = None) -> list[dict[str, Any]]:
    filt: dict = {}
    if local:
        filt["local"] = local
    cursor = _responsables_col().find(filt).sort("nombre", 1)
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results


def add_responsable(
    nombre: str, rol: str, local: str, franquiciado_id: str = "grido_default"
) -> str:
    doc = {
        "nombre": nombre,
        "rol": rol,
        "local": local,
        "franquiciado_id": franquiciado_id,
        "created_at": datetime.now(timezone.utc),
    }
    r = _responsables_col().insert_one(doc)
    return str(r.inserted_id)


def delete_responsable(resp_id: str) -> bool:
    from bson import ObjectId
    r = _responsables_col().delete_one({"_id": ObjectId(resp_id)})
    return r.deleted_count > 0


# ══════════════════════════════════════════════════════════════════════════
# Colección: decisiones
# ══════════════════════════════════════════════════════════════════════════


def _decisiones_col():
    uri = _get_uri()
    if not uri:
        raise RuntimeError("MONGODB_URI not configured")
    client = _connect(uri)
    return client["grido_audit"]["decisiones"]


def create_decision(
    desvio_id: str,
    item_codigo: str,
    local: str,
    impacto: str = "",
) -> str:
    from bson import ObjectId
    doc = {
        "desvio_id": ObjectId(desvio_id),
        "item_codigo": item_codigo,
        "local": local,
        "impacto": impacto,
        "propuesta": "",
        "estado_decision": "pendiente",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    r = _decisiones_col().insert_one(doc)
    return str(r.inserted_id)


def update_decision(decision_id: str, updates: dict) -> bool:
    from bson import ObjectId
    updates["updated_at"] = datetime.now(timezone.utc)
    r = _decisiones_col().update_one(
        {"_id": ObjectId(decision_id)}, {"$set": updates}
    )
    return r.modified_count > 0


def get_decisiones_pendientes(local: str | None = None) -> list[dict[str, Any]]:
    filt: dict = {"estado_decision": "pendiente"}
    if local:
        filt["local"] = local
    cursor = _decisiones_col().find(filt).sort("created_at", -1)
    results = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["desvio_id"] = str(doc["desvio_id"])
        results.append(doc)
    return results
