"""Tabular transformer (PyTorch) — features as tokens + real self-attention (TabTransformer-style).

Reuses the shared _train_torch loop; the paper-relevant knobs (heads, embedding size, layers,
epochs) are params.
"""

from __future__ import annotations

from typing import Any

from laboratree_sdk import Component, ComponentKind, ComponentSpec, Port, RunContext, register

from . import _train_torch


@register
class TransformerModel(Component):
    spec = ComponentSpec(
        kind=ComponentKind.MODEL,
        id="model.dl.transformer",
        name="Transformer (PyTorch, tabular)",
        summary="Self-attention over the features-as-tokens (TabTransformer-style) — the same "
        "mechanism behind BERT/GPT/ViT, on tabular data. Auto-detects classification vs regression.",
        params_schema={
            "type": "object",
            "required": ["target"],
            "properties": {
                "target": {"type": "string", "title": "Target column"},
                "features": {"type": "array", "items": {"type": "string"}, "title": "Features"},
                "test_size": {"type": "number", "default": 0.25},
                "nhead": {"type": "integer", "default": 2, "title": "Attention heads"},
                "d_model": {"type": "integer", "default": 32, "title": "Embedding size"},
                "layers": {"type": "integer", "default": 2, "title": "Encoder layers"},
                "epochs": {"type": "integer", "default": 60, "title": "Training epochs"},
            },
        },
        inputs=[Port(name="dataset", dtype="dataset")],
        outputs=[Port(name="metrics", dtype="metrics")],
        tags=["dl", "pytorch", "transformer", "attention", "classification", "regression"],
    )

    def run(self, ctx: RunContext) -> dict[str, Any]:
        from torch import nn

        nhead = int(ctx.params.get("nhead", 2))
        d_model = int(ctx.params.get("d_model", 32))
        d_model -= d_model % max(1, nhead)  # keep divisible by heads
        n_layers = int(ctx.params.get("layers", 2))

        def build(k: int, out: int):
            import torch

            class Net(nn.Module):
                def __init__(self):
                    super().__init__()
                    self.emb_w = nn.Parameter(torch.randn(k, d_model) * 0.2)
                    self.emb_b = nn.Parameter(torch.zeros(k, d_model))
                    enc = nn.TransformerEncoderLayer(
                        d_model, nhead, dim_feedforward=d_model * 2, batch_first=True,
                        dropout=0.1, norm_first=True,
                    )
                    self.encoder = nn.TransformerEncoder(enc, num_layers=n_layers)
                    self.head = nn.Linear(d_model, out)

                def forward(self, x):  # x: (batch, k)
                    t = x.unsqueeze(-1) * self.emb_w + self.emb_b
                    return self.head(self.encoder(t).mean(dim=1))

            return Net()

        return _train_torch(self, ctx, build)
