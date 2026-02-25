"""
Grido Audit Vision — Capa de datos (MongoDB Atlas).
Almacena fotos comprimidas y metadata de auditoría.

Cada documento en la colección 'photos':
{
    local:       str   — nombre del local
    fecha:       str   — "YYYY-MM"
    section:     str   — "A".."E"
    item_id:     str   — "A.1", "B.4", etc.
    photo_name:  str   — "A1_001.jpg"
    photo_data:  bytes — JPEG comprimido
    size_bytes:  int
    created_at:  datetime
}
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import streamlit as st

_client = None
_db = None


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
    """Return list of distinct (local, fecha) combinations."""
    pipeline = [
        {"$group": {"_id": {"local": "$local", "fecha": "$fecha"}}},
        {"$sort": {"_id.fecha": -1, "_id.local": 1}},
    ]
    result = _col().aggregate(pipeline)
    return [{"local": doc["_id"]["local"], "fecha": doc["_id"]["fecha"]} for doc in result]
