"""RNN/LSTM family — the MLP base plus a REAL trained LSTM cell, gate by gate.

Trains a tiny torch LSTMCell (+ linear head) on the real rows read as sequences, then replays
the demo row step by step computing the gates BY HAND from the trained weights — so the
lesson's forget/input/output dials and the cell-state conveyor show true numbers.
"""

from __future__ import annotations

from . import register_tracer
from .nn import trace_nn
from .schema import ModelTrace

SEQ_LEN = 8  # timesteps shown (first features of the row, in order)
HIDDEN = 4
EPOCHS = 8
MAX_ROWS = 200


def _lstm_demo(X, y, feats, task) -> dict | None:
    import numpy as np
    import torch

    used = feats[: min(SEQ_LEN, len(feats))]
    T = len(used)
    if T < 2:
        return None
    Xa = np.asarray(X[used].iloc[:MAX_ROWS], dtype=float)
    Xa = (Xa - Xa.mean(0)) / (Xa.std(0) + 1e-9)
    ya = np.asarray(y.iloc[:MAX_ROWS], dtype=float)

    torch.manual_seed(0)
    cell = torch.nn.LSTMCell(1, HIDDEN)
    head = torch.nn.Linear(HIDDEN, 1)
    opt = torch.optim.Adam([*cell.parameters(), *head.parameters()], lr=0.05)
    loss_fn = torch.nn.BCEWithLogitsLoss() if task == "classification" else torch.nn.MSELoss()
    xb = torch.tensor(Xa, dtype=torch.float32)
    yb = torch.tensor(ya, dtype=torch.float32)
    if task == "classification":
        yb = (yb > 0.5).float() if yb.max() > 1 else yb

    for _ in range(EPOCHS):  # real (tiny) training so the gates are learned, not random
        opt.zero_grad()
        h = torch.zeros(len(xb), HIDDEN)
        c = torch.zeros(len(xb), HIDDEN)
        for t in range(T):
            h, c = cell(xb[:, t : t + 1], (h, c))
        loss = loss_fn(head(h).squeeze(-1), yb)
        loss.backward()
        opt.step()

    # replay the demo row computing gates BY HAND from the trained weights
    with torch.no_grad():
        w_ih, w_hh = cell.weight_ih, cell.weight_hh
        b = cell.bias_ih + cell.bias_hh
        h1 = torch.zeros(HIDDEN)
        c1 = torch.zeros(HIDDEN)
        steps = []
        for t in range(T):
            x = xb[0, t : t + 1]
            z = w_ih @ x + w_hh @ h1 + b
            i, f, g, o = z[:HIDDEN], z[HIDDEN : 2 * HIDDEN], z[2 * HIDDEN : 3 * HIDDEN], z[3 * HIDDEN :]
            i, f, o = torch.sigmoid(i), torch.sigmoid(f), torch.sigmoid(o)
            g = torch.tanh(g)
            c1 = f * c1 + i * g
            h1 = o * torch.tanh(c1)
            steps.append({
                "t": t + 1,
                "feature": used[t],
                "x": round(float(x[0]), 2),
                "i": round(float(i.mean()), 2),  # input gate: how much new info to write
                "f": round(float(f.mean()), 2),  # forget gate: how much memory to keep
                "o": round(float(o.mean()), 2),  # output gate: how much memory to reveal
                "c": round(float(c1.mean()), 2),  # the cell state (the conveyor belt)
                "h": round(float(h1.mean()), 2),
            })
    return {"steps": steps, "hidden": HIDDEN, "final_loss": round(float(loss), 4)}


@register_tracer("rnn")
def trace_rnn(X, y, feats, target, task, labels, params=None) -> ModelTrace:
    base = trace_nn(X, y, feats, target, task, labels, params=params)
    try:
        lstm = _lstm_demo(X, y, feats, task)
    except Exception:  # torch unavailable or shape trouble — the nn lesson still plays
        lstm = None
    if lstm:
        base.series = {**(base.series or {}), "lstm": lstm}
        base.note = (
            "An LSTM reads the input step by step. A cell state (the conveyor belt) carries "
            "memory forward; three learned gates decide, at every step, what to erase (forget), "
            "what to write (input), and what to reveal (output). The dials in the lesson are "
            "this trained cell's real gate activations on your data."
        )
    return base
