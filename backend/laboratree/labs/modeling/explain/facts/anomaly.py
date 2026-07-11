"""Curated facts for the anomaly-detection models (3)."""

from __future__ import annotations

from . import Alternative, HyperparameterDoc, ModelFacts, register_facts


def _alt(model: str, when: str) -> Alternative:
    return Alternative(model=model, prefer_when=when)


def _hp(name: str, plain: str, effect: str, rng: str = "") -> HyperparameterDoc:
    return HyperparameterDoc(name=name, plain=plain, effect=effect, typical_range=rng)


register_facts(ModelFacts(
    key="isolation_forest", display_name="Isolation Forest", family="anomaly",
    one_liner="Weird points get boxed in by random cuts in just a few slices.",
    pros=["Fast and scalable — linear-ish time", "Handles many dimensions well",
          "No distance metric or density assumptions"],
    cons=["Scores are relative, not calibrated probabilities",
          "Misses LOCAL anomalies inside globally normal regions"],
    limitations=["Contamination must be guessed to set the alert threshold"],
    use_when=["Big datasets, global outliers, first-pass fraud/defect screening."],
    alternatives=[
        _alt("Local Outlier Factor", "anomalies are local — odd for their neighbourhood"),
        _alt("One-Class SVM", "you have clean 'normal-only' training data"),
    ],
    hyperparameters=[
        _hp("contamination", "The share of rows you expect to be anomalies.",
            "Directly moves the alert threshold — the business decision knob.", "0.01–0.1"),
    ],
))

register_facts(ModelFacts(
    key="lof", display_name="Local Outlier Factor", family="anomaly",
    one_liner="Compares your crowdedness to your neighbors' — catches local oddballs.",
    pros=["Finds anomalies RELATIVE to their local neighbourhood",
          "No global density assumption"],
    cons=["O(n²) neighbour searches — doesn't scale", "Sensitive to k (n_neighbors)"],
    limitations=["High dimensions blur the neighbourhoods it depends on"],
    use_when=["Datasets with regions of different density — suburb vs downtown."],
    alternatives=[
        _alt("Isolation Forest", "data is large or anomalies are global"),
        _alt("One-Class SVM", "you want a learned boundary around normal"),
    ],
    hyperparameters=[
        _hp("n_neighbors", "The size of 'my neighbourhood' (k).",
            "Small = very local verdicts; large = smoother, more global.", "10–50"),
        _hp("contamination", "Expected anomaly share.", "Sets the alert threshold.", "0.01–0.1"),
    ],
))

register_facts(ModelFacts(
    key="one_class_svm", display_name="One-Class SVM", family="anomaly",
    one_liner="Shrink-wraps a boundary around normal; outside means anomaly.",
    pros=["Learns a flexible boundary (kernels)", "Solid theory; works in high dimensions with scaling"],
    cons=["Assumes the training data is (almost) all normal", "Kernel + ν tuning is fiddly; scales poorly"],
    limitations=["Polluted training data poisons the boundary"],
    use_when=["You can collect clean normal-only data (healthy machines, valid transactions)."],
    alternatives=[
        _alt("Isolation Forest", "training data already contains anomalies"),
        _alt("Local Outlier Factor", "anomalies are local density dips"),
    ],
    hyperparameters=[
        _hp("nu", "Upper bound on the fraction allowed outside the wrap (ν).",
            "Bigger ν = looser wrap, more rows flagged.", "0.01–0.2"),
    ],
))
