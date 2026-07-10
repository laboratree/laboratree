"""Causal-inference tracer — real estimation on a realistic teaching design.

Causal models need identification structure (random assignment, pre/post periods, an
instrument) that an arbitrary Learning-Lab dataset rarely has. So — exactly as a textbook does
— each lesson estimates a seeded, realistic scenario with KNOWN ground truth, fits the real
estimator, and animates the actual numbers:
  * rct -> a job-training RCT: the difference in group means IS the effect
  * did -> a minimum-wage DiD: treated vs control, before vs after (the 2×2 table)
  * iv  -> a returns-to-schooling IV: the two OLS stages, and how it beats confounded OLS
"""

from __future__ import annotations

from . import register_tracer
from .schema import ModelTrace

SPEC: list[dict] = []
N = 400


def _rct():
    import numpy as np
    from scipy import stats

    rng = np.random.default_rng(7)
    t = rng.integers(0, 2, N)  # randomised assignment
    true = 1200.0  # true effect of training on earnings ($)
    y = 24000 + true * t + rng.normal(0, 3000, N)
    treated, control = y[t == 1], y[t == 0]
    ate = float(treated.mean() - control.mean())
    tstat, pval = stats.ttest_ind(treated, control, equal_var=False)
    se = abs(ate / float(tstat))
    return {
        "kind": "rct", "unit": "$ earnings", "true_effect": true,
        "treated_mean": round(float(treated.mean()), 1),
        "control_mean": round(float(control.mean()), 1),
        "ate": round(ate, 1), "se": round(se, 1),
        "ci_low": round(ate - 1.96 * se, 1), "ci_high": round(ate + 1.96 * se, 1),
        "p_value": round(float(pval), 4),
        "n_treated": int((t == 1).sum()), "n_control": int((t == 0).sum()),
        # a small sample of points for the dot-plot
        "treated_pts": [round(float(v), 0) for v in treated[:30]],
        "control_pts": [round(float(v), 0) for v in control[:30]],
    }


def _did():
    import numpy as np
    import pandas as pd
    import statsmodels.formula.api as smf

    rng = np.random.default_rng(11)
    g = rng.integers(0, 2, N)  # treated state (raised its minimum wage) vs control
    post = rng.integers(0, 2, N)  # after the policy vs before
    # employment level: state gap + a common time trend + the treatment effect on treated&post
    true = -2.5
    y = 80 + 6 * g + 4 * post + true * (g * post) + rng.normal(0, 3, N)
    df = pd.DataFrame({"y": y, "g": g, "t": post})
    res = smf.ols("y ~ g + t + g:t", data=df).fit()

    def cell(gi, ti):
        return round(float(df[(df.g == gi) & (df.t == ti)].y.mean()), 2)

    return {
        "kind": "did", "unit": "employment", "true_effect": true,
        "treated_pre": cell(1, 0), "treated_post": cell(1, 1),
        "control_pre": cell(0, 0), "control_post": cell(0, 1),
        "did_effect": round(float(res.params["g:t"]), 3),
        "p_value": round(float(res.pvalues["g:t"]), 4),
    }


def _iv():
    import numpy as np
    import statsmodels.api as sm

    rng = np.random.default_rng(13)
    z = rng.integers(0, 2, N)  # instrument: near a college (nudges schooling, not wages directly)
    ability = rng.normal(0, 1, N)  # UNOBSERVED confounder — raises schooling AND wages
    school = 12 + 2.0 * z + 1.5 * ability + rng.normal(0, 0.6, N)
    true = 0.08  # true return to a year of schooling (log wage)
    logw = 2.0 + true * school + 0.5 * ability + rng.normal(0, 0.3, N)

    z1 = sm.add_constant(z.astype(float))
    s1 = sm.OLS(school, z1).fit()
    school_hat = s1.predict(z1)
    s2 = sm.OLS(logw, sm.add_constant(school_hat)).fit()
    naive = sm.OLS(logw, sm.add_constant(school)).fit()
    return {
        "kind": "iv", "unit": "log wage", "true_effect": true,
        "first_stage_slope": round(float(s1.params[1]), 3),
        "first_stage_F": round(float(s1.fvalue), 1),
        "iv_effect": round(float(s2.params[1]), 4),
        "naive_ols_effect": round(float(naive.params[1]), 4),
        "p_value": round(float(s2.pvalues[1]), 4),
        "weak_instrument": bool(s1.fvalue < 10),
    }


def _rdd():
    import numpy as np
    import statsmodels.api as sm

    rng = np.random.default_rng(17)
    r = rng.uniform(-10, 10, N)  # running variable (e.g. a test score), cutoff at 0
    treat = (r >= 0).astype(float)
    true = 8.0  # the jump at the cutoff (e.g. scholarship raises later earnings)
    y = 40 + 1.2 * r + true * treat + rng.normal(0, 4, N)
    Xr = sm.add_constant(np.column_stack([treat, r, treat * r]))
    res = sm.OLS(y, Xr).fit()
    # a downsampled scatter + the two local lines for the animation
    idx = np.argsort(r)[:: max(1, N // 60)]
    left = [{"r": round(float(r[i]), 2), "y": round(float(y[i]), 2)} for i in idx if r[i] < 0]
    right = [{"r": round(float(r[i]), 2), "y": round(float(y[i]), 2)} for i in idx if r[i] >= 0]
    b = res.params
    return {
        "kind": "rdd", "unit": "outcome", "true_effect": true,
        "rd_effect": round(float(b[1]), 3),
        "p_value": round(float(res.pvalues[1]), 4),
        "intercept": round(float(b[0]), 2), "slope": round(float(b[2 - 0] if False else b[2]), 3),
        "jump_lo": round(float(b[0]), 2), "jump_hi": round(float(b[0] + b[1]), 2),
        "left": left, "right": right,
    }


_BUILDERS = {"rct": _rct, "did": _did, "iv": _iv, "rdd": _rdd}


@register_tracer("causal")
def trace_causal(X, y, feats, target, task, labels, params=None) -> ModelTrace:
    params = dict(params or {})
    model = str(params.pop("_model", "rct") or "rct")
    builder = _BUILDERS.get(model, _rct)
    try:
        mech = builder()
    except Exception:
        mech = None
    note = (
        "Causal models don't just predict — they estimate what a treatment CAUSED, under an "
        "identification strategy. This lesson estimates a classic, realistic design for real "
        "so you can watch the effect come out of the numbers."
    )
    return ModelTrace(
        family="causal", target=target, task="causal", features=feats[:6], labels=None,
        series={"mechanism": mech} if mech else None,
        test_rows=[], params={}, param_spec=[], note=note,
    )
