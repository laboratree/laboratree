"""Transformer family — a tiny REAL self-attention model (TabTransformer-style) on the data.

Each row's features become TOKENS. A real torch MultiheadAttention layer is trained on the data,
and the trace carries the genuine attention matrices — averaged over training for the Training
view, and per held-out row for the Testing view — so the animation shows which features the model
actually learned to "listen to".
"""

from __future__ import annotations

from . import register_tracer
from .common import lbl, resolve_params, split_holdout, table_rows
from .schema import ModelTrace

MAX_TOKENS = 8
TRAIN_CAP = 400

SPEC = [
    {"key": "nhead", "label": "Attention heads", "type": "select", "default": "2",
     "options": ["1", "2", "4"],
     "help": "Parallel attention 'viewpoints' — each head can learn a different relationship."},
    {"key": "d_model", "label": "Embedding size", "type": "select", "default": "16",
     "options": ["8", "16", "32"],
     "help": "How many numbers represent each token internally."},
    {"key": "epochs", "label": "Training epochs", "type": "int", "default": 40, "min": 10,
     "max": 120, "step": 10, "help": "How many passes over the data the model trains for."},
]


@register_tracer("transformer")
def trace_transformer(X, y, feats, target, task, labels, params=None) -> ModelTrace:
    import numpy as np
    import torch
    from sklearn.preprocessing import StandardScaler
    from torch import nn

    p, param_spec = resolve_params(SPEC, params)
    nhead, d_model, epochs = int(p["nhead"]), int(p["d_model"]), int(p["epochs"])

    # tokens = the most target-correlated features (the drawn matrix matches the trained model)
    corr = [(f, abs(float(np.corrcoef(X[f], y)[0, 1]) if X[f].std() else 0.0)) for f in feats]
    corr.sort(key=lambda t: -t[1])
    toks = [f for f, _ in corr[:MAX_TOKENS]]
    k = len(toks)
    if k < 2:
        raise ValueError("need at least 2 numeric features for an attention model")

    Xtr, Xte, ytr, yte = split_holdout(X[toks], y)
    scaler = StandardScaler().fit(Xtr)
    n_out = int(y.nunique()) if task == "classification" else 1

    class TabAttn(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb_w = nn.Parameter(torch.randn(k, d_model) * 0.2)  # per-feature embedding
            self.emb_b = nn.Parameter(torch.zeros(k, d_model))
            self.attn = nn.MultiheadAttention(d_model, nhead, batch_first=True)
            self.head = nn.Linear(d_model, n_out)

        def forward(self, x):  # x: (batch, k) standardized values
            t = x.unsqueeze(-1) * self.emb_w + self.emb_b  # (batch, k, d_model)
            a, w = self.attn(t, t, t, need_weights=True, average_attn_weights=False)
            pooled = (t + a).mean(dim=1)  # residual + mean-pool over tokens
            return self.head(pooled), w  # w: (batch, nhead, k, k)

    torch.manual_seed(1729)
    net = TabAttn()
    m = min(TRAIN_CAP, len(Xtr))
    xb = torch.tensor(scaler.transform(Xtr.iloc[:m]), dtype=torch.float32)
    yb = torch.tensor(
        ytr.iloc[:m].to_numpy().astype("int64" if task == "classification" else "float32")
    )
    loss_fn = nn.CrossEntropyLoss() if task == "classification" else nn.MSELoss()
    opt = torch.optim.Adam(net.parameters(), lr=5e-3)

    def mats(w) -> list[list[list[float]]]:  # (nhead, k, k) -> rounded python lists
        return [[[round(float(v), 3) for v in row] for row in head] for head in w]

    def snapshot(epoch: int) -> dict:
        net.eval()
        with torch.no_grad():
            _, w = net(xb)
        net.train()
        return {"epoch": epoch, "attention": mats(w.mean(dim=0))}

    # attention SHARPENING — the state between stages: untrained (flat) -> mid -> trained (focused)
    attention_stages = [snapshot(0)]
    net.train()
    for e in range(1, epochs + 1):
        opt.zero_grad()
        out, _ = net(xb)
        loss_fn(out if task == "classification" else out.squeeze(-1), yb).backward()
        opt.step()
        if e in (max(1, epochs // 2), epochs):
            attention_stages.append(snapshot(e))

    net.eval()
    with torch.no_grad():
        _, wtr = net(xb)
        mean_attn = mats(wtr.mean(dim=0))
        xt = torch.tensor(scaler.transform(Xte), dtype=torch.float32)
        logits, wte = net(xt)
        if task == "classification":
            preds = logits.argmax(dim=1).numpy()
        else:
            preds = logits.squeeze(-1).numpy()

    test_rows = []
    for j in range(len(Xte)):
        pred = lbl(preds[j], task, labels)
        actual = lbl(yte.iloc[j], task, labels)
        test_rows.append({
            "values": {f: round(float(Xte.iloc[j][f]), 3) for f in X.columns[:24] if f in Xte},
            "attention": mats(wte[j]),
            "predicted": pred, "actual": actual,
            "correct": (pred == actual) if task == "classification" else None,
            "error": None if task == "classification" else round(float(preds[j]) - float(yte.iloc[j]), 3),
        })

    return ModelTrace(
        family="transformer", target=target, task=task, features=toks, labels=labels,
        table=table_rows(X, y, toks, target, task, labels),
        series={
            "attention": mean_attn, "heads": nhead, "d_model": d_model,
            "attention_stages": attention_stages,
        },
        test_rows=test_rows, params=p, param_spec=param_spec,
        note="A transformer turns each feature into a TOKEN, and self-attention lets every token "
        "look at every other token and decide how much to listen to it (Q·K match → softmax → "
        "weights). The heatmap shows those real learned weights; multiple heads learn different "
        "relationships in parallel. BERT/GPT/ViT run this same mechanism over words or image "
        "patches instead of features.",
    )
