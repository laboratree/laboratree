"""Helpers shared by every family tracer: X/y prep, label formatting, sample tables, holdout."""

from __future__ import annotations


def prep_xy(df, target, task_hint=None):
    """Numeric feature matrix X, numeric-coded target y, task, and the label names.

    Robust to messy real data: rather than dropping every row with ANY missing value (which
    wipes wide datasets), it drops only rows with a missing TARGET, then median-imputes the
    feature columns. Drops ID-like columns (leakage) and shuffles rows (files are often sorted
    by class, which would make the tail-of-file holdout single-class).

    ``task_hint`` ("classification"|"regression") lets the caller force the model's intended
    task — so a Linear Regression model on a binary target is treated as regression (a linear
    probability model), not silently swapped to logistic.
    """
    import pandas as pd

    from ..evaluation.metrics import id_like

    if target not in df.columns:
        target = df.columns[-1]
    df = df[df[target].notna()].sample(frac=1.0, random_state=42).reset_index(drop=True)
    if len(df) < 4:
        raise ValueError("not enough complete rows to fit a model (need at least 4)")

    y_raw = df[target]
    numeric_target = pd.api.types.is_numeric_dtype(y_raw)
    n_classes = int(y_raw.nunique())
    if task_hint in ("classification", "regression"):
        task = task_hint
    elif numeric_target and n_classes > 10:
        task = "regression"
    else:
        task = "classification"

    labels = None
    if task == "regression":
        if numeric_target:
            y = y_raw.astype(float)  # ordinary regression (or a linear probability model on 0/1)
        elif n_classes == 2:
            # a BINARY string target under a regression model = linear probability model:
            # code it 0/1 and fit a real line (NOT logistic). Keep the names for display.
            cat = y_raw.astype("category")
            y = cat.cat.codes.astype(float)
            labels = list(cat.cat.categories.astype(str))
        else:
            # a multi-class string target can't be regressed — fall back honestly
            task = "classification"
    if task == "classification":
        cat = y_raw.astype("category")
        y = cat.cat.codes.astype(float)
        labels = list(cat.cat.categories.astype(str))

    feats = [
        c for c in df.select_dtypes("number").columns
        if c != target and not id_like(df[c], c)
    ]
    X = df[feats]
    if X.isna().any().to_numpy().any():  # median-impute scattered gaps instead of dropping rows
        X = X.fillna(X.median(numeric_only=True)).fillna(0.0)
    return X, y, feats, task, labels


def lbl(v, task, labels):
    return labels[int(v)] if (task == "classification" and labels) else round(float(v), 3)


def table_rows(X, y, feats, target, task, labels, n=40):
    rows = []
    for i in range(min(n, len(X))):
        r = {f: round(float(X.iloc[i][f]), 3) for f in feats}
        r[target] = lbl(y.iloc[i], task, labels)
        rows.append(r)
    return rows


def split_holdout(X, y):
    n = len(X)
    # always leave at least 1 training and 1 test row (guards tiny datasets → empty fit)
    ntest = min(6, max(1, n // 5))
    ntest = min(ntest, n - 1)
    return X.iloc[:-ntest], X.iloc[-ntest:], y.iloc[:-ntest], y.iloc[-ntest:]


def resolve_params(spec: list[dict], user: dict | None) -> tuple[dict, list[dict]]:
    """Merge user-supplied hyperparameters over a family's declared defaults, coercing + clamping
    to keep the refit safe, and return (values, param_spec) — the spec carries the live ``value`` so
    the UI renders sliders/selects seeded with the paper's (or user's) settings.

    Each spec item: {key, label, type: 'int'|'float'|'select', default, min?, max?, step?, options?, help?}.
    """
    user = user or {}
    values: dict = {}
    out: list[dict] = []
    for s in spec:
        key, typ = s["key"], s["type"]
        v = user.get(key, s["default"])
        try:
            if typ == "int":
                v = int(round(float(v)))
            elif typ == "float":
                v = float(v)
        except (TypeError, ValueError):
            v = s["default"]
        if typ in ("int", "float"):
            if "min" in s:
                v = max(s["min"], v)
            if "max" in s:
                v = min(s["max"], v)
        elif typ == "select" and v not in s.get("options", []):
            v = s["default"]
        values[key] = v
        out.append({**s, "value": v})
    return values, out
