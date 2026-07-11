"""Policy Research flow — the platform's policy use case.

The machinery is the NGO-education scenario's executor set (that scenario remains this flow's
demo content); the canonical key is ``policy-research``, with ``ngo-policy`` kept as an alias so
existing canvases keep working.
"""

from __future__ import annotations

from .. import alias_flow
from . import ngo_education  # noqa: F401 — ensures the source executors are registered

FLOW_KEY = "policy-research"

alias_flow(ngo_education.FLOW_KEY, FLOW_KEY)
