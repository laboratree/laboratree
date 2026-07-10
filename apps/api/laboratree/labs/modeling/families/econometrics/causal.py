"""Causal-inference models — the econometrician's toolkit for 'did X CAUSE Y?'.

Prediction models fit patterns; these estimate TREATMENT EFFECTS under an identification
strategy:
  * RCT / A-B test          -> randomisation makes a simple mean difference causal
  * Difference-in-Differences -> compare the before→after change of treated vs control
  * Instrumental Variables   -> use an instrument to strip endogeneity via two OLS stages
"""

from __future__ import annotations

from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register


def _num(df, col):
    import pandas as pd

    return pd.to_numeric(df[col], errors="coerce")


@register
class RCTModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.causal.rct",
        name="RCT / A-B test",
        summary="Randomised experiment: because treatment was assigned by coin flip, the simple "
        "difference in group means IS the causal effect — with a confidence interval.",
        params_schema={
            "type": "object",
            "required": ["outcome", "treatment"],
            "properties": {
                "outcome": {"type": "string", "title": "Outcome column"},
                "treatment": {"type": "string", "title": "Treatment column (0/1)"},
            },
        },
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["causal", "experiment", "regression-family:econometrics"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import pandas as pd
        from scipy import stats

        df: pd.DataFrame = ctx.inputs["dataset"].dropna(
            subset=[ctx.params["outcome"], ctx.params["treatment"]]
        )
        y = _num(df, ctx.params["outcome"])
        t = _num(df, ctx.params["treatment"])
        uniq = sorted(t.dropna().unique())
        if len(uniq) == 2:  # binary treatment: split by its two values
            control, treated = y[t == uniq[0]], y[t == uniq[1]]
        else:  # continuous 'dose': split at the median
            thr = t.median()
            treated, control = y[t > thr], y[t <= thr]
        if len(treated) < 2 or len(control) < 2:
            raise ValueError("RCT needs at least 2 treated and 2 control observations.")
        ate = float(treated.mean() - control.mean())
        tstat, pval = stats.ttest_ind(treated, control, equal_var=False)
        se = abs(ate / float(tstat)) if tstat else float("nan")
        metrics = {
            "ate": round(ate, 4), "t_stat": round(float(tstat), 3),
            "p_value": round(float(pval), 4),
            "ci_low": round(float(ate - 1.96 * se), 4), "ci_high": round(float(ate + 1.96 * se), 4),
        }
        for k, v in metrics.items():
            ctx.emit(k, v, kind="metric", component=self.spec.id)
        return {
            "metrics": metrics, "task": "causal", "n_obs": int(len(df)),
            "treated_mean": round(float(treated.mean()), 4),
            "control_mean": round(float(control.mean()), 4),
            "n_treated": int(len(treated)), "n_control": int(len(control)),
        }


@register
class DiffInDiffModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.causal.did",
        name="Difference-in-Differences",
        summary="Compares the before→after change of a treated group against a control group; the "
        "interaction term is the causal effect (assuming parallel trends).",
        params_schema={
            "type": "object",
            "required": ["outcome", "treated_group", "post_period"],
            "properties": {
                "outcome": {"type": "string", "title": "Outcome column"},
                "treated_group": {"type": "string", "title": "Treated-group flag (0/1)"},
                "post_period": {"type": "string", "title": "Post-treatment period flag (0/1)"},
            },
        },
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["causal", "panel", "regression-family:econometrics"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import pandas as pd
        import statsmodels.formula.api as smf

        p = ctx.params
        df: pd.DataFrame = ctx.inputs["dataset"].dropna(
            subset=[p["outcome"], p["treated_group"], p["post_period"]]
        ).copy()
        df["_y"] = _num(df, p["outcome"])
        df["_g"] = (_num(df, p["treated_group"]) > 0).astype(int)
        df["_t"] = (_num(df, p["post_period"]) > 0).astype(int)
        res = smf.ols("_y ~ _g + _t + _g:_t", data=df).fit()
        did = float(res.params["_g:_t"])
        cell = {
            "treated_pre": round(float(df[(df._g == 1) & (df._t == 0)]._y.mean()), 4),
            "treated_post": round(float(df[(df._g == 1) & (df._t == 1)]._y.mean()), 4),
            "control_pre": round(float(df[(df._g == 0) & (df._t == 0)]._y.mean()), 4),
            "control_post": round(float(df[(df._g == 0) & (df._t == 1)]._y.mean()), 4),
        }
        metrics = {
            "did_effect": round(did, 4),
            "t_stat": round(float(res.tvalues["_g:_t"]), 3),
            "p_value": round(float(res.pvalues["_g:_t"]), 4),
            "r2": round(float(res.rsquared), 4),
        }
        for k, v in metrics.items():
            ctx.emit(k, v, kind="metric", component=self.spec.id)
        return {"metrics": metrics, "task": "causal", "n_obs": int(len(df)), "cells": cell}


@register
class IVModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.causal.iv",
        name="Instrumental Variables (2SLS)",
        summary="When the treatment is endogenous, an instrument (affects treatment, not the "
        "outcome directly) recovers the causal effect via two OLS stages.",
        params_schema={
            "type": "object",
            "required": ["outcome", "endogenous", "instrument"],
            "properties": {
                "outcome": {"type": "string", "title": "Outcome (Y)"},
                "endogenous": {"type": "string", "title": "Endogenous regressor (X)"},
                "instrument": {"type": "string", "title": "Instrument (Z)"},
                "controls": {"type": "array", "items": {"type": "string"}, "title": "Controls"},
            },
        },
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["causal", "regression-family:econometrics"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import numpy as np
        import pandas as pd
        import statsmodels.api as sm

        p = ctx.params
        cols = [p["outcome"], p["endogenous"], p["instrument"], *(p.get("controls") or [])]
        df: pd.DataFrame = ctx.inputs["dataset"].dropna(subset=cols).copy()
        y = _num(df, p["outcome"]).to_numpy(dtype=float)
        x = _num(df, p["endogenous"]).to_numpy(dtype=float)
        z = _num(df, p["instrument"]).to_numpy(dtype=float)
        ctrl = np.column_stack([_num(df, c).to_numpy(dtype=float) for c in (p.get("controls") or [])]) \
            if p.get("controls") else np.empty((len(df), 0))

        # stage 1: regress the endogenous X on the instrument (+ controls) → fitted X̂
        z1 = sm.add_constant(np.column_stack([z, ctrl]))
        s1 = sm.OLS(x, z1).fit()
        x_hat = s1.predict(z1)
        first_stage_f = float(s1.fvalue)
        # stage 2: regress Y on the FITTED X̂ (+ controls) → the causal (LATE) coefficient
        z2 = sm.add_constant(np.column_stack([x_hat, ctrl]))
        s2 = sm.OLS(y, z2).fit()
        # naive OLS for the endogeneity-bias contrast
        naive = sm.OLS(y, sm.add_constant(np.column_stack([x, ctrl]))).fit()

        metrics = {
            "iv_effect": round(float(s2.params[1]), 4),
            "naive_ols_effect": round(float(naive.params[1]), 4),
            "first_stage_F": round(first_stage_f, 2),
            "p_value": round(float(s2.pvalues[1]), 4),
        }
        for k, v in metrics.items():
            ctx.emit(k, v, kind="metric", component=self.spec.id)
        weak = first_stage_f < 10  # the rule-of-thumb weak-instrument flag
        return {"metrics": metrics, "task": "causal", "n_obs": int(len(df)),
                "weak_instrument": bool(weak)}


@register
class RDDModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.causal.rdd",
        name="Regression Discontinuity (Sharp)",
        summary="When treatment switches ON at a cutoff of a running variable, the JUMP in the "
        "outcome right at the cutoff is the causal effect — units just above and below are alike.",
        params_schema={
            "type": "object",
            "required": ["outcome", "running", "cutoff"],
            "properties": {
                "outcome": {"type": "string", "title": "Outcome (Y)"},
                "running": {"type": "string", "title": "Running variable (assignment score)"},
                "cutoff": {"type": "number", "title": "Cutoff value"},
                "bandwidth": {"type": "number", "default": 0.0,
                              "title": "Bandwidth (0 = use all data)"},
            },
        },
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["causal", "regression-family:econometrics"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        import numpy as np
        import statsmodels.api as sm

        p = ctx.params
        df = ctx.inputs["dataset"].dropna(subset=[p["outcome"], p["running"]]).copy()
        y = _num(df, p["outcome"]).to_numpy(dtype=float)
        r = _num(df, p["running"]).to_numpy(dtype=float)
        cut = float(p["cutoff"])
        centered = r - cut
        bw = float(p.get("bandwidth", 0) or 0)
        if bw > 0:
            keep = np.abs(centered) <= bw
            y, centered = y[keep], centered[keep]
        treat = (centered >= 0).astype(float)
        # local linear with a treatment×slope interaction: the treat coefficient is the jump
        Xr = sm.add_constant(np.column_stack([treat, centered, treat * centered]))
        res = sm.OLS(y, Xr).fit()
        effect = float(res.params[1])
        metrics = {
            "rd_effect": round(effect, 4),
            "t_stat": round(float(res.tvalues[1]), 3),
            "p_value": round(float(res.pvalues[1]), 4),
            "n_left": int((centered < 0).sum()), "n_right": int((centered >= 0).sum()),
        }
        for k, v in metrics.items():
            ctx.emit(k, v, kind="metric", component=self.spec.id)
        return {"metrics": metrics, "task": "causal", "n_obs": int(len(y)), "cutoff": cut}
