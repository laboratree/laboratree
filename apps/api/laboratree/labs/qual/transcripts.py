"""Transcript store — Mongo documents keyed by MediaAsset id (the first real Mongo workload).

Document shape::

    {"_id": "<asset_id>", "org_id": "<org>", "language": "en", "text": "...",
     "segments": [{"start": 0.0, "end": 4.2, "text": "..."}]}

Reads are org-checked; segment edits are human corrections and land in-place.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from ...core.db.mongo import db

log = logging.getLogger(__name__)

COLLECTION = "transcripts"


async def save_transcript(
    asset_id: uuid.UUID,
    org_id: uuid.UUID,
    *,
    segments: list[dict[str, Any]],
    text: str,
    language: str = "",
) -> None:
    await db()[COLLECTION].replace_one(
        {"_id": str(asset_id)},
        {
            "_id": str(asset_id),
            "org_id": str(org_id),
            "language": language,
            "text": text,
            "segments": segments,
        },
        upsert=True,
    )
    log.info("transcript saved for asset %s (%d segments)", asset_id, len(segments))


async def get_transcript(asset_id: uuid.UUID, org_id: uuid.UUID) -> dict[str, Any] | None:
    doc = await db()[COLLECTION].find_one({"_id": str(asset_id), "org_id": str(org_id)})
    if doc is not None:
        doc.pop("org_id", None)
    return doc


async def update_segment_text(
    asset_id: uuid.UUID, org_id: uuid.UUID, index: int, new_text: str
) -> bool:
    """Human correction of one segment; rebuilds the full text. Returns False if out of range."""
    doc = await db()[COLLECTION].find_one({"_id": str(asset_id), "org_id": str(org_id)})
    if doc is None or not (0 <= index < len(doc.get("segments", []))):
        return False
    doc["segments"][index]["text"] = new_text
    doc["text"] = " ".join(s.get("text", "") for s in doc["segments"]).strip()
    await db()[COLLECTION].replace_one({"_id": str(asset_id)}, doc)
    log.info("transcript segment %d corrected for asset %s", index, asset_id)
    return True


async def delete_transcript(asset_id: uuid.UUID, org_id: uuid.UUID) -> None:
    await db()[COLLECTION].delete_one({"_id": str(asset_id), "org_id": str(org_id)})


__all__ = ["save_transcript", "get_transcript", "update_segment_text", "delete_transcript"]
