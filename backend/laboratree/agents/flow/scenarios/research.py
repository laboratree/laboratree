"""Research flow (overall) — the general end-to-end research use case.

Reuses the shared executor machinery; its stage sequence (see ``api/flows.py``) adds a
``literature`` stage with NO executor on purpose: the Supervisor spawns the DeepAgent for it
(scholarly search + synthesis), which is exactly the gap-filler pattern.
"""

from __future__ import annotations

from .. import alias_flow
from . import ngo_education

FLOW_KEY = "research"

alias_flow(ngo_education.FLOW_KEY, FLOW_KEY)
