"""Scenario flows — concrete, use-case-specific phase executors.

The flow ENGINE lives one level up (`agents/flow`); each module here registers the executors for
one flow key via ``@phase``. Importing this package registers every scenario.
"""

from __future__ import annotations

from . import ngo_education  # noqa: F401 — registers the ngo-policy executors

__all__ = ["ngo_education"]
