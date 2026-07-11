"""Shared dataset persistence — one way to turn a dataframe into a versioned Dataset row."""

from __future__ import annotations

import io
import logging
import uuid

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from ..projects.models import Dataset
from .repro import dataframe_hash
from .storage import get_blob_store

log = logging.getLogger(__name__)


async def store_dataframe(
    session: AsyncSession, *, org_id: uuid.UUID, project_id: uuid.UUID,
    name: str, df: pd.DataFrame, prefix: str = "datasets",
) -> Dataset:
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    key = f"{prefix}/{project_id}/{uuid.uuid4()}.csv"
    get_blob_store().put(key, buf.getvalue())
    dataset = Dataset(org_id=org_id, project_id=project_id, name=name, storage_key=key,
                      content_hash=dataframe_hash(df), n_rows=int(len(df)),
                      n_cols=int(df.shape[1]))
    session.add(dataset)
    await session.flush()
    log.info("stored dataset %r (%dx%d) for project %s", name, len(df), df.shape[1], project_id)
    return dataset


__all__ = ["store_dataframe"]
