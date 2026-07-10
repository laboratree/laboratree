"""Curated facts for the deep-learning models (3)."""

from __future__ import annotations

from . import Alternative, HyperparameterDoc, ModelFacts, register_facts


def _alt(model: str, when: str) -> Alternative:
    return Alternative(model=model, prefer_when=when)


def _hp(name: str, plain: str, effect: str, rng: str = "") -> HyperparameterDoc:
    return HyperparameterDoc(name=name, plain=plain, effect=effect, typical_range=rng)


register_facts(ModelFacts(
    key="cnn", display_name="CNN", family="nn",
    one_liner="A small detector slides everywhere; pooling keeps the strongest evidence.",
    pros=["Weight sharing: learns a pattern ONCE, finds it anywhere",
          "Far fewer parameters than a dense net on grid data",
          "The backbone of image, audio and signal models"],
    cons=["Needs meaningful local structure — shuffled columns kill it",
          "Data-hungry; architecture choices multiply"],
    limitations=["On plain tabular data (no locality) it rarely beats trees"],
    use_when=["Images, spectrograms, sensor traces — anything where NEIGHBOURING values mean something."],
    alternatives=[
        _alt("MLP", "features have no spatial order to exploit"),
        _alt("Transformer", "long-range dependencies matter more than local ones"),
        _alt("XGBoost", "it's really a table, not a grid"),
    ],
    hyperparameters=[
        _hp("channels", "How many different detectors (filters) per layer.",
            "More channels = more pattern types learned, more compute.", "8–64"),
        _hp("epochs", "Passes over the training data.", "Watch validation loss for the stopping point.", "10–100"),
    ],
))

register_facts(ModelFacts(
    key="rnn", display_name="RNN / LSTM / GRU", family="nn",
    one_liner="A cell reads the sequence step by step; gates decide what to remember.",
    pros=["Native handling of ordered data and variable lengths",
          "LSTM/GRU gates solve the vanishing-gradient problem of plain RNNs",
          "Small models do well on short sequences"],
    cons=["Sequential training — can't parallelise across time",
          "Long-range memory still degrades; transformers overtook them at scale"],
    limitations=["Plain RNN cells forget quickly — use LSTM/GRU in practice"],
    use_when=["Short-to-medium sequences with modest data: sensor streams, demand series, text snippets."],
    alternatives=[
        _alt("Transformer", "long sequences and lots of data"),
        _alt("SARIMA/ETS", "one clean seasonal series — classical models are stronger and explainable"),
        _alt("XGBoost on lag features", "you can engineer the memory yourself"),
    ],
    hyperparameters=[
        _hp("cell", "The recurrence type: lstm, gru, or plain rnn.",
            "LSTM = 3 gates (most capacity); GRU = 2 gates (leaner); RNN = none (fastest, forgets).", "lstm"),
        _hp("hidden", "Size of the hidden state (the memory).", "Bigger = more memory, more overfit risk.", "16–128"),
        _hp("bidirectional", "Read the sequence both ways.", "Helps when the future context is available.", "off"),
        _hp("epochs", "Passes over the data.", "Watch validation loss.", "10–100"),
    ],
))

register_facts(ModelFacts(
    key="transformer", display_name="Transformer", family="transformer",
    one_liner="Every token attends to every other token — the architecture behind GPT.",
    pros=["Attention sees long-range structure in one hop",
          "Fully parallel training (no recurrence)",
          "Scales further than any earlier architecture"],
    cons=["Attention is O(n²) in sequence length", "Very data-hungry; small-data results disappoint"],
    limitations=["On small tabular datasets it's usually outgunned by boosted trees"],
    use_when=["Large datasets where relationships span the whole input: language, long series, "
              "many interacting features."],
    alternatives=[
        _alt("LSTM/GRU", "short sequences, small data, tight compute"),
        _alt("XGBoost", "ordinary tabular data"),
    ],
    hyperparameters=[
        _hp("nhead", "Parallel attention heads.", "Each head learns a different 'who listens to whom'.", "2–8"),
        _hp("d_model", "Width of the token embeddings.", "Bigger = more expressive, more data needed.", "32–256"),
        _hp("layers", "Stacked attention blocks.", "Depth compounds context mixing.", "1–6"),
        _hp("epochs", "Passes over the data.", "Watch validation loss.", "10–100"),
    ],
))
