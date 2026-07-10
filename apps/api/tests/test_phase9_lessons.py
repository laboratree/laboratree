"""Guided model lessons (Learning Lab P1): resolve chains, generic lesson structure, catalog."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from laboratree.labs.modeling.lessons import build_lesson, catalog_entries, lesson_keys
from laboratree.labs.modeling.lessons._steps import MAX_LESSON_BYTES, TABLE_ROWS
from laboratree.labs.modeling.lessons.schema import Lesson

GENERIC_CHAPTERS = [
    "roadmap", "the-data", "training", "the-math", "testing", "hyperparameters", "verdict",
    "self-check",
]


def _binary_csv(n: int = 60) -> bytes:
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "age": rng.normal(50, 10, n).round(1),
            "bp": rng.normal(120, 15, n).round(1),
            "chol": rng.normal(200, 30, n).round(1),
        }
    )
    df["disease"] = ((df.age * 0.05 + df.bp * 0.02 + rng.normal(0, 1, n)) > 5.0).astype(int)
    return df.to_csv(index=False).encode()


def test_resolve_chains():
    assert lesson_keys("XGBoost") == ["xgboost", "trees"]
    assert lesson_keys("LSTM (bidirectional)") == ["lstm", "rnn", "nn"]
    assert lesson_keys("model.dl.rnn") == ["rnn", "nn"]
    assert lesson_keys("DBSCAN") == ["dbscan", "clustering"]
    assert lesson_keys("Ridge regression") == ["ridge", "regularized", "linear"]
    assert lesson_keys("Isolation Forest") == ["isolation_forest", "anomaly"]
    assert lesson_keys("") == ["trees"]  # teaching default, same as viz.build_trace
    assert lesson_keys("Some Novel Architecture 3000") == ["trees"]


N_MODELS = 60  # 46 + RDD, AR, MA, ARMA, VECM, EGARCH, GJR, MNLogit, OrdLogit, OrdProbit, WLS, GLS, RLM, ZIP


def test_every_catalog_model_resolves_to_its_own_key():
    entries = catalog_entries()
    assert len(entries) == N_MODELS
    assert len({e.key for e in entries}) == N_MODELS
    for e in entries:
        assert lesson_keys(e.component_id)[0] == e.key, e.component_id
        assert e.one_liner and e.group and e.family


def test_every_model_has_facts_and_a_tailored_lesson():
    """The breadth guarantee: EVERY model gets curated facts and a deep (non-generic) lesson
    via its own key or its family's script — no model plays the generic wrapper anymore."""
    from laboratree.labs.modeling.explain.facts import facts_for

    for e in catalog_entries():
        facts = facts_for(lesson_keys(e.component_id))
        assert facts is not None, f"{e.key} has no facts entry"
        assert facts.pros and facts.cons and facts.use_when, f"{e.key} facts incomplete"
        assert e.has_deep_lesson, f"{e.key} should resolve to a deep lesson script"


# every model's lesson must animate ITS OWN mechanism (widget key or stage kind)
_MECHANISM = {
    "random forest": "bootstrap-hat",
    "extra trees": "bootstrap-hat",
    "adaboost": "weight-grow",
    "bagging": "bootstrap-hat",
    "gaussian process": "gp-band",
    "SVM": "margin-street",
    "naive bayes": "bayes-race",
    "fixed effects": "fe-demean",
}


@pytest.mark.parametrize(("model", "widget"), sorted(_MECHANISM.items()))
def test_every_model_animates_its_own_mechanism(model: str, widget: str):
    les = build_lesson(_binary_csv(), "disease", model, None)
    widgets = {s.widget for c in les.chapters for s in c.steps if s.widget}
    assert widget in widgets, f"{model} lesson missing its {widget} animation"


def _blob_csv():
    """Two clear blobs + a few outliers so clustering has real structure to find."""
    rng = np.random.default_rng(0)
    a = rng.normal([0, 0], 0.6, (50, 2))
    b = rng.normal([4, 4], 0.6, (50, 2))
    xy = np.vstack([a, b, rng.uniform(-2, 6, (6, 2))])
    df = pd.DataFrame({"f1": xy[:, 0].round(2), "f2": xy[:, 1].round(2),
                       "f3": rng.normal(size=len(xy)).round(2), "grp": 0})
    return df.to_csv(index=False).encode()


@pytest.mark.parametrize(("model", "kind", "stage"), [
    ("DBSCAN", "dbscan", "dbscan-real"),
    ("gaussian mixture", "gmm", "gmm-real"),
    ("hierarchical clustering", "hierarchical", "dendrogram-real"),
    ("spectral clustering", "spectral", "spectral-real"),
])
def test_clustering_uses_real_per_algorithm_mechanism(model, kind, stage):
    les = build_lesson(_blob_csv(), "grp", model, None)
    mech = (les.trace.series or {}).get("mechanism")
    assert mech and mech["kind"] == kind, f"{model} must emit real {kind} mechanism"
    assert mech["points"], f"{kind} mechanism has no real points"
    kinds = {s.anim.kind for c in les.chapters for s in c.steps if s.anim}
    assert stage in kinds, f"{model} lesson must render the real {stage} stage"


def test_dbscan_mechanism_has_core_border_noise():
    les = build_lesson(_blob_csv(), "grp", "DBSCAN", None)
    mech = (les.trace.series or {})["mechanism"]
    roles = {p["role"] for p in mech["points"]}
    assert roles <= {"core", "border", "noise"} and "core" in roles
    assert mech["eps"] > 0 and mech["n_clusters"] >= 1


def test_gmm_mechanism_has_responsibilities_and_ellipses():
    les = build_lesson(_blob_csv(), "grp", "gaussian mixture", None)
    mech = (les.trace.series or {})["mechanism"]
    assert len(mech["ellipses"]) == mech["k"]
    for p in mech["points"]:
        assert abs(sum(p["resp"]) - 1.0) < 0.05, "responsibilities must sum to ~1"


def test_hierarchical_mechanism_is_a_valid_tree():
    les = build_lesson(_blob_csv(), "grp", "hierarchical clustering", None)
    mech = (les.trace.series or {})["mechanism"]
    assert len(mech["merges"]) == mech["n_leaves"] - 1  # a binary tree of n leaves
    assert all(mech["merges"][i]["height"] <= mech["merges"][i + 1]["height"] + 1e-6
               for i in range(len(mech["merges"]) - 1)), "merge heights must be non-decreasing"


@pytest.mark.parametrize(("model", "kind", "stage"), [
    ("isolation forest", "isolation_forest", "iforest-real"),
    ("LOF", "lof", "lof-real"),
    ("one-class svm", "one_class_svm", "ocsvm-real"),
])
def test_anomaly_uses_real_per_algorithm_mechanism(model, kind, stage):
    les = build_lesson(_blob_csv(), "grp", model, None)
    mech = (les.trace.series or {}).get("mechanism")
    assert mech and mech["kind"] == kind, f"{model} must emit real {kind} mechanism"
    assert mech["points"], f"{kind} mechanism has no real points"
    kinds = {s.anim.kind for c in les.chapters for s in c.steps if s.anim}
    assert stage in kinds, f"{model} lesson must render the real {stage} stage"


def test_iforest_mechanism_has_pathlength_histogram():
    les = build_lesson(_blob_csv(), "grp", "isolation forest", None)
    mech = (les.trace.series or {})["mechanism"]
    assert mech["c_n"] > 0 and len(mech["hist"]) == len(mech["edges"]) - 1
    assert all("depth" in p for p in mech["points"])


def test_lof_mechanism_flags_a_local_outlier():
    les = build_lesson(_blob_csv(), "grp", "LOF", None)
    mech = (les.trace.series or {})["mechanism"]
    assert mech["focus"]["lof"] > 1.0  # the top outlier must be a genuine local outlier
    assert len(mech["focus"]["neighbors"]) == mech["k"]


def test_ocsvm_mechanism_has_a_boundary_grid():
    les = build_lesson(_blob_csv(), "grp", "one-class svm", None)
    mech = (les.trace.series or {})["mechanism"]
    assert mech["grid"] and len(mech["grid"]) == len(mech["gy"])
    assert len(mech["grid"][0]) == len(mech["gx"])


def _series_csv():
    rng = np.random.default_rng(1)
    n = 140
    t = np.arange(n)
    return pd.DataFrame({
        "ret": rng.normal(0, 1, n).round(3), "x1": rng.normal(size=n).round(2),
        "x2": rng.normal(size=n).round(2), "sales": (50 + 0.5 * t + rng.normal(0, 3, n)).round(2),
    }).to_csv(index=False).encode()


@pytest.mark.parametrize(("model", "stage"), [
    ("RCT", "rct-real"),
    ("difference-in-differences", "did-real"),
    ("instrumental variables", "iv-real"),
    ("regression discontinuity", "rdd-real"),
])
def test_causal_lessons_estimate_real_designs(model, stage):
    les = build_lesson(_series_csv(), "ret", model, None)
    mech = (les.trace.series or {}).get("mechanism")
    assert mech is not None
    kinds = {s.anim.kind for c in les.chapters for s in c.steps if s.anim}
    assert stage in kinds, f"{model} must render the real {stage} stage"
    # the estimator must land near the seeded ground truth
    if mech["kind"] == "rct":
        assert abs(mech["ate"] - mech["true_effect"]) < 400
    elif mech["kind"] == "did":
        assert abs(mech["did_effect"] - mech["true_effect"]) < 1.5
    elif mech["kind"] == "iv":
        assert abs(mech["iv_effect"] - mech["true_effect"]) < abs(
            mech["naive_ols_effect"] - mech["true_effect"])


@pytest.mark.parametrize("model", ["ARCH", "GARCH"])
def test_volatility_lessons_fit_real_conditional_vol(model):
    les = build_lesson(_series_csv(), "sales", model, None)
    mech = (les.trace.series or {}).get("mechanism")
    assert mech and mech["kind"] == model.lower()
    assert len(mech["vol"]) == len(mech["returns"]) and mech["vol"], "conditional vol path missing"
    kinds = {s.anim.kind for c in les.chapters for s in c.steps if s.anim}
    assert "volatility-real" in kinds


def test_new_econ_models_are_deep_with_facts():
    from laboratree.labs.modeling.explain.facts import facts_for

    for key in ["quantile", "negative_binomial", "arch", "garch", "var", "rct", "did", "iv"]:
        f = facts_for([key])
        assert f and f.pros and f.applications and f.exam_questions, f"{key} drill incomplete"


def test_timeseries_mechanisms():
    rng = np.random.default_rng(2)
    t = np.arange(120)
    reg = pd.DataFrame({
        "x1": rng.normal(size=120).round(2),
        "sales": (50 + 0.5 * t + 8 * np.sin(t / 6) + rng.normal(0, 2, 120)).round(2),
    })
    csv = reg.to_csv(index=False).encode()
    ets = build_lesson(csv, "sales", "exponential smoothing", None)
    assert any(s.widget == "decompose-stack" for c in ets.chapters for s in c.steps)
    sar = build_lesson(csv, "sales", "SARIMA", None)
    assert any(s.widget == "differencing" for c in sar.chapters for s in c.steps)


def test_neural_lessons_use_real_tracer_data():
    """P4: CNN gets a real conv/pool walkthrough, LSTM gets real gate dials, and the nn
    family gets the three-optimizer race — all computed from the fitted traces."""
    cnn = build_lesson(_binary_csv(), "disease", "CNN", None)
    kinds = {s.anim.kind for c in cnn.chapters for s in c.steps if s.anim}
    assert "conv-slide" in kinds and "max-pool" in kinds
    conv = (cnn.trace.series or {}).get("conv")
    assert conv and conv["grid"] and conv["fmap"] and conv["pooled"]

    lstm = build_lesson(_binary_csv(), "disease", "LSTM", None)
    kinds = {s.anim.kind for c in lstm.chapters for s in c.steps if s.anim}
    assert "lstm-gates" in kinds
    steps = ((lstm.trace.series or {}).get("lstm") or {}).get("steps") or []
    assert steps and all(0.0 <= s["f"] <= 1.0 and 0.0 <= s["i"] <= 1.0 for s in steps)

    mlp = build_lesson(_binary_csv(), "disease", "MLP neural network", None)
    opts = (mlp.trace.series or {}).get("optimizers") or {}
    kinds = {s.anim.kind for c in mlp.chapters for s in c.steps if s.anim}
    assert len(opts) >= 2 and "optimizer-race" in kinds


def test_every_model_builds_on_its_own_example_dataset():
    """The user's fix: every model defaults to a data subset that actually fits it —
    regression models get a numeric outcome, classification a categorical one, etc."""
    from laboratree.labs.modeling.examples import example_for

    for e in catalog_entries():
        ex = example_for(e.key)
        assert ex.csv and ex.target, f"{e.key} has no example dataset"
        les = build_lesson(ex.csv, ex.target, e.key, None)
        assert les.chapters, f"{e.key} lesson failed to build on its example"
        # a pure regression model must produce a regression trace on its example (never logistic)
        if e.family == "linear" and e.task.startswith("regression"):
            assert les.trace.task == "regression", f"{e.key} should be regression on its example"
        # a classification-only model must produce a classification trace
        if e.task == "classification" and e.family in ("linear", "trees"):
            assert les.trace.task == "classification", f"{e.key} should be classification"


@pytest.mark.parametrize("model", ["Linear Regression", "Ridge", "OLS", "WLS", "Robust Regression"])
def test_regression_models_animate_the_best_fit_line(model):
    """The user's ask: fit the line, and link each actual point to its predicted point (residuals)."""
    from laboratree.labs.modeling.examples import example_for

    ex = example_for(model)
    les = build_lesson(ex.csv, ex.target, model, None)
    rf = (les.trace.series or {}).get("regression_fit")
    assert rf and rf["points"], f"{model} must emit best-fit-line geometry"
    # each point carries actual (y) and predicted-on-line (yhat) — the residual is their gap
    assert all("y" in p and "yhat" in p for p in rf["points"])
    assert rf["sse_line"] <= rf["sse_mean"] and 0 <= rf["r2"] <= 1  # the line beats the flat mean
    kinds = {s.anim.kind for c in les.chapters for s in c.steps if s.anim}
    assert "regression-fit" in kinds, f"{model} lesson must render the regression-fit animation"


def test_example_profiles_match_model_shape():
    from laboratree.labs.modeling.examples import example_for

    assert "image" in example_for("cnn").name.lower()  # CNN → image-like data
    assert example_for("linear_regression").task == "regression"  # not classification
    assert example_for("garch").task == "volatility"
    assert example_for("kmeans").task == "clustering"
    assert example_for("arima").task == "forecasting"


def test_every_model_has_drill_content():
    """Exam-prep guarantee: applications, edge cases and exam Q&A exist for ALL models."""
    from laboratree.labs.modeling.explain.facts import facts_for

    for e in catalog_entries():
        facts = facts_for([e.key])
        assert facts is not None, e.key
        assert facts.applications, f"{e.key} has no applications"
        assert facts.edge_cases, f"{e.key} has no edge cases"
        assert facts.exam_questions, f"{e.key} has no exam questions"


def test_every_lesson_ends_with_a_quiz():
    les = build_lesson(_binary_csv(), "disease", "XGBoost", None)
    quiz = les.chapters[-1]
    assert quiz.id == "self-check" and quiz.steps[0].quiz, "xgboost lesson must end in a quiz"
    assert any("Derive the optimal leaf value" in qa.q for qa in quiz.steps[0].quiz)
    les2 = build_lesson(_binary_csv(), "disease", "k-nearest neighbors", None)
    assert les2.chapters[-1].id == "self-check" and les2.chapters[-1].steps[0].quiz


def test_econometrics_lessons_carry_inference():
    les = build_lesson(_binary_csv(), "disease", "logit", None)
    ids = [c.id for c in les.chapters]
    assert "inference-table" in ids and "odds-ratios" in ids
    inf = (les.trace.series or {}).get("inference")
    assert inf and inf["kind"] == "logit"
    rows = [r for r in inf["rows"] if r["feature"] != "intercept"]
    assert rows and all("se" in r and "p" in r and "ci_lo" in r for r in rows)
    assert all("exp_coef" in r for r in rows), "logit rows must carry odds ratios"

    les_ols = build_lesson(_binary_csv(), "bp", "OLS regression", None)
    ids_ols = [c.id for c in les_ols.chapters]
    assert "inference-table" in ids_ols and "assumptions" in ids_ols


def test_panel_lessons_play():
    for model in ("pooled OLS", "fixed effects", "random effects"):
        les = build_lesson(_binary_csv(), "bp", model, None)
        ids = [c.id for c in les.chapters]
        assert "demeaning" in ids and "three-estimators" in ids, model
        demean = next(c for c in les.chapters if c.id == "demeaning")
        assert demean.steps[0].widget == "fe-demean"


def test_family_lessons_use_live_numbers():
    """Family scripts must interpolate the fitted trace's numbers, not canned examples."""
    les = build_lesson(_binary_csv(), "disease", "logistic regression", None)
    coefs = les.trace.coef or []
    assert coefs
    lead = str(coefs[0]["feature"])
    # the lead coefficient must appear somewhere in the narration (odds-logodds / odds-ratio)
    all_narr = " ".join(s.narration for c in les.chapters for s in c.steps)
    all_worked = " ".join(m.worked for c in les.chapters for s in c.steps for m in s.math)
    assert lead in (all_narr + all_worked)


def test_logistic_vs_linear_regression_are_distinct_and_correct():
    """The user's bug: Linear Regression must NOT show logistic (sigmoid/logit); Logistic must."""
    csv = _binary_csv()  # binary 'disease' target
    log = build_lesson(csv, "disease", "Logistic Regression", None)
    lin = build_lesson(csv, "disease", "Linear Regression", None)
    log_ids = [c.id for c in log.chapters]
    lin_ids = [c.id for c in lin.chapters]
    # logistic teaches the logit link, the sigmoid, and log-loss
    assert {"why-not-a-line", "odds-logodds", "sigmoid", "logloss"} <= set(log_ids)
    assert log.trace.task == "classification"
    # linear regression is REGRESSION (least squares) with no sigmoid/logit chapters
    assert lin.trace.task == "regression", "linear regression must fit a real line, not logistic"
    assert not ({"sigmoid", "logloss", "odds-logodds"} & set(lin_ids))
    # and its knobs are the regression knobs (alpha), never the logistic C
    keys = {s.get("key") for s in (lin.param_spec or [])}
    assert "C" not in keys

    les = build_lesson(_binary_csv(), "disease", "k-means", None)
    loop = next(c for c in les.chapters if c.id == "loop")
    assert "ASSIGN" in loop.steps[0].narration


def test_generic_lesson_structure():
    # only truly UNKNOWN models fall back to the generic wrapper now (no facts → no quiz)
    les = build_lesson(_binary_csv(), "disease", "some mystery architecture", None)
    assert les.model == "trees" and les.family == "trees"
    assert [c.id for c in les.chapters] == [c for c in GENERIC_CHAPTERS if c != "self-check"]
    assert les.total_ms == sum(s.duration_ms for c in les.chapters for s in c.steps)
    for c in les.chapters:
        assert c.steps, c.id
        for s in c.steps:
            assert s.narration.strip(), f"{c.id}/{s.id} has empty narration"
    data_step = les.chapters[1].steps[0]
    assert data_step.table is not None and len(data_step.table.rows) <= TABLE_ROWS
    assert data_step.table.target_col == "disease"
    assert data_step.anim is not None and data_step.anim.kind == "data-table"


def test_lesson_schema_roundtrip_and_budget():
    les = build_lesson(_binary_csv(), "disease", "gradient boosting", None)
    payload = les.model_dump_json()
    assert len(payload.encode()) < MAX_LESSON_BYTES
    assert Lesson.model_validate_json(payload).model == les.model


@pytest.mark.parametrize("model", ["mlp", "knn", "kmeans", "isolation forest", "logit"])
def test_lesson_plays_for_other_families(model: str):
    les = build_lesson(_binary_csv(), "disease", model, None)
    assert les.chapters and les.total_ms > 0
    assert [c.id for c in les.chapters][0] == "roadmap"
    assert len(les.model_dump_json().encode()) < MAX_LESSON_BYTES


def test_clustering_lesson_reads_unsupervised():
    les = build_lesson(_binary_csv(), "disease", "k-means", None)
    narration = les.chapters[1].steps[0].narration
    assert "NO answer column" in narration


def test_hyperparameter_chapter_lists_live_knobs():
    les = build_lesson(_binary_csv(), "disease", "XGBoost", None)
    knobs = next(c for c in les.chapters if c.id == "hyperparameters")
    assert knobs.steps[0].anim is not None and knobs.steps[0].anim.kind == "hyperparams"
    assert les.param_spec, "lesson must mirror the trace's tunable knobs"


# ---- P2: the exact-math XGBoost tracer ---------------------------------------------------------


def test_split_math_hand_checked():
    from laboratree.labs.modeling.viz._split_math import entropy, gini, mse, quantile_thresholds

    y = np.array([0, 0, 0, 1, 1])  # p = [0.6, 0.4]
    assert gini(y) == pytest.approx(1 - (0.6**2 + 0.4**2))  # 0.48
    assert entropy(y) == pytest.approx(-(0.6 * np.log2(0.6) + 0.4 * np.log2(0.4)))
    assert gini(np.array([1, 1, 1])) == 0.0 and entropy(np.array([1, 1, 1])) == 0.0
    assert mse(np.array([2.0, 4.0])) == pytest.approx(1.0)  # mean 3, squared devs 1,1
    ts = quantile_thresholds(np.array([1.0, 2.0, 3.0, 4.0, 5.0]), m=8)
    assert ts and all(1.0 < t < 5.0 for t in ts) and ts == sorted(ts)


def _xgb_trace(**params):
    from laboratree.labs.modeling.viz import build_trace

    return build_trace(_binary_csv(), "disease", "xgboost", params or None)


def test_xgboost_similarity_gain_and_leaves_are_exact():
    lam, gamma = 1.0, 0.0
    trace = _xgb_trace(reg_lambda=lam, gamma=gamma)
    b = trace.boosting
    assert b is not None and b.objective == "binary:logistic" and b.base_score == 0.0
    round1 = b.rounds[0]
    root = round1.root

    # base margin 0 → p = 0.5 for every row → g = 0.5−y (|g| = 0.5), h = 0.25
    assert root.stats.sum_h == pytest.approx(0.25 * root.stats.n, abs=1e-3)
    for row in round1.table:
        assert row["current"] == 0.5 and abs(row["residual"]) == 0.5
        assert row["h"] == 0.25 and abs(row["g"]) == 0.5

    def check(node):
        s = node.stats
        assert s.similarity == pytest.approx(s.sum_g**2 / (s.sum_h + lam), abs=2e-3)
        for t in node.trials:
            assert t.left.n + t.right.n == s.n
            assert t.gain == pytest.approx(
                t.left.similarity + t.right.similarity - s.similarity - gamma, abs=2e-3
            )
        if node.leaf:
            assert node.value == pytest.approx(-s.sum_g / (s.sum_h + lam), abs=2e-3)
        else:
            kept = [t for t in node.trials if t.kept]
            assert len(kept) == 1 and kept[0].gain == max(
                t.gain for t in node.trials if t.eligible
            )
            check(node.left)
            check(node.right)

    for r in b.rounds:
        check(r.root)


def test_xgboost_matches_native_root_split():
    xgb = pytest.importorskip("xgboost")
    import io

    from laboratree.labs.modeling.viz import build_trace
    from laboratree.labs.modeling.viz.common import prep_xy, split_holdout

    rng = np.random.default_rng(3)
    n = 80
    df = pd.DataFrame(
        {
            "x1": rng.integers(0, 5, n).astype(float),
            "x2": rng.integers(0, 5, n).astype(float),
        }
    )
    df["y"] = ((df.x1 >= 3).astype(int) ^ (rng.uniform(size=n) < 0.05)).astype(int)
    data = df.to_csv(index=False).encode()

    trace = build_trace(data, "y", "xgboost", {"max_depth": 1, "n_estimators": 1, "eta": 0.3})
    root = trace.boosting.rounds[0].root
    assert not root.leaf

    X, y, feats, _task, _labels = prep_xy(pd.read_csv(io.BytesIO(data), nrows=2000), "y")
    Xtr, _Xte, ytr, _yte = split_holdout(X, y)
    clf = xgb.XGBClassifier(
        n_estimators=1, max_depth=1, learning_rate=0.3, reg_lambda=1.0, gamma=0.0,
        min_child_weight=1.0, base_score=0.5, tree_method="exact",
        objective="binary:logistic",
    )
    clf.fit(Xtr, ytr.astype(int))
    booster = clf.get_booster().trees_to_dataframe()
    split_row = booster[booster.Feature != "Leaf"].iloc[0]

    assert root.feature == split_row.Feature
    ours = (Xtr[root.feature] <= root.threshold).to_numpy()
    native = (Xtr[str(split_row.Feature)] < float(split_row.Split)).to_numpy()
    assert (ours == native).all(), "same rows must go left as in native XGBoost"


def test_xgboost_eta_moves_round2_predictions():
    trace = _xgb_trace(eta=0.5, n_estimators=2)
    b = trace.boosting
    assert b is not None and len(b.rounds) == 2
    r2 = b.rounds[1].table
    assert any(row["current"] != 0.5 for row in r2), "after round 1 the predictions must move"
    # test rows carry the assembled boosting score + per-round contributions
    tr = (trace.test_rows or [])[0]
    assert "rounds" in tr and "boost_score" in tr
    assert tr["boost_score"] == pytest.approx(
        (trace.baseline or 0) + sum(c["value"] for c in tr["rounds"]), abs=5e-3
    )
