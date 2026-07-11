"""Neural-network family — MLP / deep-learning style models.

Training view: the layer structure + a forward pass. Testing view: input -> hidden activations ->
output for each held-out row.
"""

from __future__ import annotations

from . import register_tracer
from .common import lbl, resolve_params, split_holdout, table_rows
from .schema import ModelTrace

SPEC = [
    {"key": "hidden", "label": "Hidden units", "type": "int", "default": 5, "min": 2, "max": 12,
     "step": 1, "help": "Neurons in the hidden layer — more = more capacity to fit complex patterns."},
    {"key": "activation", "label": "Activation", "type": "select", "default": "tanh",
     "options": ["tanh", "relu", "logistic"],
     "help": "The squashing function each hidden unit applies to its weighted input."},
    {"key": "max_iter", "label": "Training epochs", "type": "int", "default": 150, "min": 50,
     "max": 500, "step": 50, "help": "How many passes over the data the network trains for."},
]


_RACE_EPOCHS = 80


def _optimizer_race(Model, hidden, act, Xs, ysub, classes, task) -> dict | None:
    """Three quick REAL fits of the same net — sgd / sgd+momentum / adam — loss curves only."""
    import numpy as np

    variants = {
        "sgd": {"solver": "sgd", "momentum": 0.0, "learning_rate_init": 0.01},
        "momentum": {"solver": "sgd", "momentum": 0.9, "learning_rate_init": 0.01},
        "adam": {"solver": "adam", "learning_rate_init": 0.001},
    }
    out: dict[str, list[float]] = {}
    for name, kw in variants.items():
        try:
            net = Model(hidden_layer_sizes=(hidden,), activation=act, random_state=0,
                        max_iter=_RACE_EPOCHS, **kw)
            net.fit(Xs, ysub)
            lc = [float(v) for v in (getattr(net, "loss_curve_", None) or [])]
            if len(lc) >= 2:
                idx = np.unique(np.linspace(0, len(lc) - 1, min(40, len(lc))).round().astype(int))
                out[name] = [round(lc[i], 4) for i in idx]
        except Exception:  # a diverging variant shouldn't kill the lesson
            continue
    return out if len(out) >= 2 else None


@register_tracer("nn")
def trace_nn(X, y, feats, target, task, labels, params=None) -> ModelTrace:
    import numpy as np
    from sklearn.neural_network import MLPClassifier, MLPRegressor
    from sklearn.preprocessing import StandardScaler

    p, param_spec = resolve_params(SPEC, params)
    act = p["activation"]
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    Xtr, Xte, ytr, yte = split_holdout(X, y)
    m = min(600, len(Xs) - len(Xte))
    Model = MLPClassifier if task == "classification" else MLPRegressor
    net = Model(hidden_layer_sizes=(p["hidden"],), activation=act, random_state=0)
    show = feats[:6]

    # train EPOCH BY EPOCH (partial_fit) so we can snapshot the state between stages: the same
    # demo row's output drifting toward the truth as the loss falls.
    epochs = int(p["max_iter"])
    ysub = y.iloc[:m]
    classes = np.unique(ysub) if task == "classification" else None
    marks = {1, max(2, epochs // 10), max(3, epochs // 2), epochs}
    epoch_stages = []
    demo = Xs[0]
    truth = y.iloc[0]
    for e in range(1, epochs + 1):
        if task == "classification":
            net.partial_fit(Xs[:m], ysub, classes=classes)
        else:
            net.partial_fit(Xs[:m], ysub)
        if e in marks:
            hid = demo @ net.coefs_[0] + net.intercepts_[0]
            hid = np.tanh(hid) if act == "tanh" else (np.maximum(0, hid) if act == "relu" else 1 / (1 + np.exp(-hid)))
            out = float(np.ravel(hid @ net.coefs_[1] + net.intercepts_[1])[0])
            epoch_stages.append({
                "epoch": e,
                "loss": round(float(getattr(net, "loss_", 0.0)), 4),
                "output": round(out, 3),
            })

    # the network's REAL training loss, epoch by epoch — downsampled to <=60 points so the
    # frontend can animate "the error rolling downhill" (gradient descent).
    lc = [float(v) for v in (getattr(net, "loss_curve_", None) or [])]
    series = None
    if len(lc) >= 2:
        idx = np.unique(np.linspace(0, len(lc) - 1, min(60, len(lc))).round().astype(int))
        series = {
            "loss_curve": [round(lc[i], 4) for i in idx],
            "epoch_stages": epoch_stages,
            "demo_truth": float(truth) if task != "classification" else None,
        }
        # the optimizer race: the SAME tiny net trained three ways (plain SGD, SGD+momentum,
        # Adam) so the lesson can show — with real curves — how the rolling style changes.
        opt_curves = _optimizer_race(Model, p["hidden"], act, Xs[:m], ysub, classes, task)
        if opt_curves:
            series["optimizers"] = opt_curves

    def _activate(z):
        if act == "relu":
            return np.maximum(0.0, z)
        if act == "logistic":
            return 1.0 / (1.0 + np.exp(-z))
        return np.tanh(z)

    def forward(scaled_row):
        hidden = _activate(scaled_row @ net.coefs_[0] + net.intercepts_[0])
        out = hidden @ net.coefs_[1] + net.intercepts_[1]
        return np.ravel(hidden), float(np.ravel(out)[0])

    preds = net.predict(scaler.transform(Xte))
    test_rows = []
    for j in range(len(Xte)):
        srow = scaler.transform(Xte.iloc[[j]])[0]
        hidden, out = forward(srow)
        pred = lbl(preds[j], task, labels)
        actual = lbl(yte.iloc[j], task, labels)
        test_rows.append({
            "values": {f: round(float(Xte.iloc[j][f]), 3) for f in feats[:24]},
            "input": [round(float(v), 2) for v in srow[: len(show)]],
            "hidden": [round(float(v), 2) for v in hidden],
            "output": round(float(out), 3),
            "predicted": pred, "actual": actual,
            "correct": (pred == actual) if task == "classification" else None,
            "error": None if task == "classification" else round(float(preds[j]) - float(yte.iloc[j]), 3),
        })
    h0, o0 = forward(Xs[0])
    # real learned weights for the literal network drawing (shown features x hidden, hidden x out)
    idx = [feats.index(f) for f in show]
    w1 = [[round(float(net.coefs_[0][i][j]), 3) for j in range(net.coefs_[0].shape[1])] for i in idx]
    w2 = [round(float(net.coefs_[1][j][0]), 3) for j in range(net.coefs_[1].shape[0])]
    return ModelTrace(
        family="nn", target=target, task=task, features=show, labels=labels,
        table=table_rows(X, y, show, target, task, labels),
        layers=[len(feats), p["hidden"], 1],
        forward={
            "input": [round(float(v), 2) for v in Xs[0][: len(show)]],
            "input_names": show,
            "hidden": [round(float(v), 2) for v in h0],
            "output": round(float(o0), 3),
            "w1": w1,
            "w2": w2,
        },
        series=series,
        test_rows=test_rows, params=p, param_spec=param_spec,
        note="Standardized feature values flow into the hidden layer (each unit is a weighted mix "
        "passed through a squashing function), then combine into the output.",
    )
