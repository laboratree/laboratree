"""Field Lab — the self-hosted survey engine (design -> publish -> collect -> monitor).

Pure, deterministic logic only (no LLM, no DB): the questionnaire structure schema + skip-logic
evaluator (``runtime``), response-quality flags (``quality``), and quota matching (``quotas``).
The API layer (``api/surveys.py``, ``api/public_survey.py``) wires these to persistence.
"""
