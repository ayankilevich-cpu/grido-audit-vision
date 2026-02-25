"""
Grido Audit Vision — Capa de datos (MongoDB Atlas).

Colecciones:
  photos         — fotos comprimidas (se purgan a los 6 meses)
  audit_results  — resultados del análisis IA (se mantienen indefinidamente)
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
