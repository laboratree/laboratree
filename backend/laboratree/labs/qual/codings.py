"""Coding store — Mongo documents holding per-asset assignments + sentiment (org-checked).

Document: {"_id": "<asset_id>", "org_id", "codebook_id", "assignments": [...], "sentiment": [...]}.
Human overrides append/remove assignments with source="human" — recorded, never silent.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from ...core.db.mongo import db

log = logging.getLogger(__name__)

COLLECTION = "codings"


async def save_coding(
    asset_id: uuid.UUID,
    org_id: uuid.UUID,
    codebook_id: uuid.UUID,
    assignments: list[dict[str, Any]],
) -> None:
    existing = await db()[COLLECTION].find_one({"_id": str(asset_id), "org_id": str(org_id)})
    sentiment = (existing or {}).get("sentiment", [])
    await db()[COLLECTION].replace_one(
        {"_id": str(asset_id)},
        {"_id": str(asset_id), "org_id": str(org_id), "codebook_id": str(codebook_id),
         "assignments": assignments, "sentiment": sentiment},
        upsert=True,
    )
    log.info("coding saved for asset %s (%d assignments)", asset_id, len(assignments))


async def save_sentiment(
    asset_id: uuid.UUID, org_id: uuid.UUID, sentiment: list[dict[str, Any]]
) -> None:
    await db()[COLLECTION].update_one(
        {"_id": str(asset_id)},
        {"$set": {"org_id": str(org_id), "sentiment": sentiment},
         "$setOnInsert": {"assignments": [], "codebook_id": None}},
        upsert=True,
    )


async def get_coding(asset_id: uuid.UUID, org_id: uuid.UUID) -> dict[str, Any] | None:
    doc = await db()[COLLECTION].find_one({"_id": str(asset_id), "org_id": str(org_id)})
    if doc is not None:
        doc.pop("org_id", None)
    return doc


async def add_human_assignment(
    asset_id: uuid.UUID, org_id: uuid.UUID, segment: int, code: str
) -> bool:
    result = await db()[COLLECTION].update_one(
        {"_id": str(asset_id), "org_id": str(org_id)},
        {"$push": {"assignments": {"segment": segment, "code": code, "confidence": None,
                                   "support": "", "source": "human"}}},
    )
    return result.matched_count > 0


async def remove_assignment(
    asset_id: uuid.UUID, org_id: uuid.UUID, segment: int, code: str
) -> bool:
    result = await db()[COLLECTION].update_one(
        {"_id": str(asset_id), "org_id": str(org_id)},
        {"$pull": {"assignments": {"segment": segment, "code": code}}},
    )
    return result.modified_count > 0


__all__ = [
    "save_coding",
    "save_sentiment",
    "get_coding",
    "add_human_assignment",
    "remove_assignment",
]
