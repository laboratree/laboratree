"""Best-effort Neo4j mirror of a persona cohort's social graph (Postgres stays source of truth)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

log = logging.getLogger(__name__)


async def mirror_cohort_graph(
    cohort_id: uuid.UUID, org_id: uuid.UUID,
    personas: list[dict[str, Any]], edges: list[dict[str, Any]],
) -> bool:
    """Write (:Persona)-[:KNOWS]->(:Persona) for a cohort. Never raises — returns success flag."""
    try:
        from ...core.db.neo4j import driver

        cid = str(cohort_id)
        async with driver().session() as s:
            for p in personas:
                await s.run(
                    "MERGE (x:Persona {handle:$h, cohort:$cid}) SET x.org_id=$org",
                    h=str(p.get("handle")), cid=cid, org=str(org_id),
                )
            for e in edges:
                await s.run(
                    "MATCH (a:Persona {handle:$a, cohort:$cid}),(b:Persona {handle:$b, cohort:$cid}) "
                    "MERGE (a)-[r:KNOWS]-(b) SET r.weight=$w",
                    a=e["a"], b=e["b"], w=e.get("weight", 0.0), cid=cid,
                )
        log.info("mirrored cohort %s graph to neo4j (%d edges)", cohort_id, len(edges))
        return True
    except Exception as exc:  # Neo4j optional — Postgres holds the authoritative edges
        log.info("neo4j mirror skipped for cohort %s: %s", cohort_id, exc)
        return False


__all__ = ["mirror_cohort_graph"]
