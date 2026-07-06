"""Pre-flight check: can this dataset actually support a model run?

Running a model on awkward data (no numeric features, a one-value target, a handful of rows) fails
deep inside sklearn with a cryptic message. `readiness_reason` catches the common cases FIRST and
returns a clear, actionable sentence the UI can show — so a node says 'why' instead of just 'failed'.
Returns None when the data looks runnable.
"""

from __future__ import annotations

from typing import Any

from .metrics import numeric_features

MIN_ROWS = 10


def readiness_reason(df: Any, target: str, features: list[str] | None = None) -> str | None:
    """A clear message explaining why a model can't run on (df, target), or None if it can."""
    import pandas as pd

    if target not in df.columns:
        cols = ", ".join(map(str, list(df.columns)[:8]))
        return f"the target column '{target}' isn't in this dataset. Available columns: {cols}."

    df = df.dropna(subset=[target])
    if len(df) < MIN_ROWS:
        return (f"only {len(df)} rows have a value for '{target}' — too few to train and test a "
                "model. Generate demo data or upload the paper's dataset with more rows.")

    feats = numeric_features(df, target, features)
    if not feats:
        return ("no usable numeric feature columns were found (the rest are text, or look like ID "
                "columns which are dropped to avoid leakage). Generate demo data, or upload the "
                "paper's real dataset with numeric predictor columns.")

    y = df[target]
    is_classification = (
        y.dtype == object
        or str(y.dtype).startswith(("category", "str", "bool"))
        or (pd.api.types.is_integer_dtype(y) and y.nunique() <= 10)
    )
    if is_classification and y.nunique() < 2:
        return (f"the target '{target}' has only one distinct value, so there's nothing to classify — "
                "a model needs at least two classes (or a varying number) to learn.")
    return None


__all__ = ["readiness_reason"]
