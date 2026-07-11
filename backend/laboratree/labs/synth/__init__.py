"""Synthetic Respondents Engine (U3) — persona-conditioned dry-runs before real fielding.

Personas are built deterministically from target margins (``personas``); each twin "takes" the real
instrument once via the LLM (``twin.simulate_persona``, injectable); the dry-run report aggregates
predicted drop-off, confusing items, and expected answer distributions (``twin.aggregate_dry_run``,
pure). Everything a twin produces is synthetic and must be labelled as such — it informs *design*
decisions, never impact claims.
"""
