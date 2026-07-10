"""Family deep lessons — a tailored, narrated show for EVERY model family.

One registered script per family key (decision_tree, gradient_boosting, linear, regularized,
nn, knn, clustering, anomaly, timeseries, transformer). Models resolve through their chain, so
e.g. Lasso hits "regularized", LSTM hits "nn", DBSCAN hits "clustering" — every one of the 35
registered models gets concept chapters, live-number math, and its own facts-driven
hyperparameter + verdict chapters. Per-model scripts (like xgboost.py) override these as the
deeper tracers land, family by family.
"""

from __future__ import annotations

from typing import Any

from ..explain.facts import ModelFacts
from ..viz.schema import ModelTrace
from . import register_lesson
from ._steps import (
    DUR_SCENE,
    DUR_SHOW,
    AnimDirective,
    Chapter,
    MathBlock,
    Symbol,
    chapter,
    data_chapter,
    explainer_for_chain,
    hyperparams_chapter,
    math_block,
    quiz_chapter,
    roadmap_chapter,
    step,
    testing_chapter,
    verdict_chapter,
)


def _note(id: str, title: str, kicker: str, narration: str,
          math: list[MathBlock] | None = None, duration_ms: int = DUR_SCENE) -> Chapter:
    return chapter(id, title, [step(id, narration, duration_ms=duration_ms,
                                    anim=AnimDirective(kind="note"), math=math)], kicker=kicker)


def _widget(id: str, title: str, kicker: str, narration: str, widget: str,
            math: list[MathBlock] | None = None) -> Chapter:
    return chapter(id, title, [step(id, narration, duration_ms=DUR_SHOW,
                                    anim=AnimDirective(kind="widget"), widget=widget,
                                    math=math)], kicker=kicker)


def _train(id: str, title: str, kicker: str, narration: str,
           math: list[MathBlock] | None = None) -> Chapter:
    return chapter(id, title, [step(id, narration, duration_ms=DUR_SHOW,
                                    anim=AnimDirective(kind="legacy-train"), math=math)],
                   kicker=kicker)


def _m(name: str, formula: str, plain: str, symbols: list[tuple[str, str]], worked: str) -> MathBlock:
    return MathBlock(name=name, formula=formula, plain=plain,
                     symbols=[Symbol(sym=s, means=m) for s, m in symbols], worked=worked)


def _finish(title: str, one_liner: str, chapters: list[Chapter], trace: ModelTrace,
            facts: ModelFacts | None, guide: dict[str, Any]) -> list[Chapter]:
    name = facts.display_name if facts else title
    tail = [testing_chapter(trace)]
    if trace.param_spec:
        tail.append(hyperparams_chapter(trace, facts))
    tail.append(verdict_chapter(facts, guide, name))
    quiz = quiz_chapter(facts, name)
    if quiz:
        tail.append(quiz)
    full = [*chapters, *tail]
    return [roadmap_chapter(title, full, one_liner), *full]


# ---- decision tree ------------------------------------------------------------------------


@register_lesson("decision_tree")
def decision_tree_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["trees"])
    scan = trace.scan or {}
    chosen = scan.get("chosen_feature")
    parent_imp = scan.get("parent_impurity")
    best = (scan.get("features") or [{}])[0]
    cls = trace.task == "classification"

    grow_nodes = _count_tree(trace.tree)
    chapters = [
        data_chapter(trace),
        _note("what-is-a-split", "What is a split?", "One question parts the table",
              "A tree learns by asking ONE question at a time — “is a column ≤ some cut-point?” "
              "— and sending each row left (yes) or right (no). A split is good when each side "
              "comes out PURER than the mixed group it came from. Everything that follows is "
              "just: find the question that un-mixes the table the most."),
        _widget("gini-balls", "Gini, as a game of balls", "Impurity = the disagreement game",
                "Put a group's outcomes in a bag and draw two at random — the chance they "
                "DISAGREE is the gini impurity. A pure group never disagrees (gini 0); a 50/50 "
                "group disagrees half the time (gini 0.5). "
                + (f"Your root group's mix-up score is {parent_imp}." if parent_imp is not None
                   else "For number targets the same role is played by the variance."),
                "gini-balls",
                math=[_m("Gini impurity", "gini = 1 − Σ pᵢ²",
                         "One minus the chance two random draws AGREE.",
                         [("pᵢ", "share of the group that is class i")],
                         f"your root: impurity = {parent_imp}" if parent_imp is not None else "")]),
        _widget("impurity-curve", "The inverted U", "Messiest in the middle",
                "Slide a group's class share from 0% to 100% and gini traces an inverted U: "
                "zero at the pure ends, worst at 50/50. Every split is trying to push both "
                "children DOWN the sides of this curve.", "impurity-curve"),
        _widget("surprise", "Entropy = expected surprise", "The other yardstick",
                "Entropy scores a group by how SURPRISED you are, on average, when you peek at "
                "a row's class: certain events carry no surprise, rare ones carry a lot. Pure "
                "group = zero surprise. Gini and entropy almost always pick the same splits — "
                "gini is just cheaper to compute.", "surprise-curve",
                math=[_m("Entropy", "H = −Σ pᵢ·log₂(pᵢ)", "The average surprise, in bits.",
                         [("pᵢ", "share of class i"), ("log₂", "surprise of one event: −log₂ p")],
                         "p = [0.5, 0.5] → H = 1 bit (a fair coin); p = [1, 0] → H = 0")]),
        _train("root-question", "Choosing the root question", "Every cut-point auditions",
               "The tree sweeps candidate cut-points on each feature and scores the "
               "information gain — how much impurity the split removes. "
               + (f"On your data “{chosen}” won with a cut at {best.get('best_t')} "
                  f"(gain {best.get('best_gain')}). Open the training view's “scan” tab to "
                  f"watch the sweep in slow motion." if chosen else
                  "Open the training view's “scan” tab to watch the sweep."),
               math=[_m("Information gain", "gain = impurity(parent) − Σ (nᵢ/n)·impurity(childᵢ)",
                        "How much cleaner the two sides are, weighted by size.",
                        [("n", "rows at the parent"), ("nᵢ", "rows going to child i")],
                        f"root: {parent_imp} − weighted children = {best.get('best_gain')}"
                        if chosen else "")] if cls or chosen else None),
        chapter("grow", "Growing the tree",
                [step("grow",
                      "Each side of the winning split repeats the hunt with only ITS rows — "
                      "depth by depth — until groups are pure, too small, or the depth cap "
                      "stops them. Deeper is not better: past a point the tree memorises noise.",
                      duration_ms=DUR_SHOW,
                      anim=AnimDirective(kind="tree-grow", substeps=max(1, grow_nodes)))],
                kicker="Repeat per depth, stop before memorising"),
    ]
    return _finish("The decision tree, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


# ---- gradient boosting ---------------------------------------------------------------------


@register_lesson("gradient_boosting")
def gradient_boosting_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["trees"])
    cls = trace.task == "classification"
    lr = (trace.params or {}).get("learning_rate", 1.0)
    n_rounds = len(trace.rounds or [])
    base = trace.baseline

    chapters = [
        data_chapter(trace),
        chapter("tree-recap", "One weak tree",
                [step("recap", "The building block is a SHALLOW tree — a weak learner. Alone "
                      "it underfits on purpose; its job is to capture the biggest, most obvious "
                      "chunk of the pattern and leave the rest.",
                      duration_ms=DUR_SCENE,
                      anim=AnimDirective(kind="tree-grow", substeps=max(1, _count_tree(trace.tree))))],
                kicker="The weak learner"),
        _note("baseline", "Start from a constant", "Round 0",
              (f"Before any tree, everyone gets the same guess: the average log-odds of the "
               f"data, {base}." if cls and base is not None else
               "Before any tree, everyone gets the same guess"
               + (f": {base}, the average outcome." if base is not None else ".")
               ) + " Boring — but now every row has an ERROR, and errors are trainable."),
        _note("residual-target", "Residuals become the target", "The core boosting move",
              "Subtract the current prediction from the truth, row by row: that's the residual "
              "column. The next tree is NOT trained on the original target — it is trained to "
              "predict the residuals. Fix what's still wrong, nothing else.",
              math=[_m("The residual", "r = y − ŷ", "What's still wrong for this row.",
                       [("y", "the truth"), ("ŷ", "the prediction so far")],
                       "truth 1, current 0.62 → r = +0.38: push this row up")]),
        _train("rounds", "Watch the rounds stack", "Tree by tree, table by table",
               f"Here is the real ensemble on your data — {n_rounds} rounds. Between trees, "
               "look at the transformed tables: predictions creep toward the truth and the "
               "residual column shrinks. Each tree splits by the same gini/variance auditions "
               "you saw in the decision-tree lesson.",
               math=[_m("The update", "F_new(x) = F_old(x) + η·tree(x)",
                        "Add a shrunken correction each round.",
                        [("η", f"learning rate — here {lr}"),
                         ("tree(x)", "the new tree's output for row x")],
                        f"η = {lr}: each tree's correction counts at {float(lr) * 100:.0f}%")]),
        (
            _widget("assembly", "From score to answer", "Assembling a prediction",
                    "To predict, a row walks down EVERY tree; the leaf outputs (times η) are "
                    "summed onto the baseline and the sigmoid squeezes the total into a "
                    "probability.", "sigmoid-squeeze",
                    math=[math_block(m) for m in guide.get("math", [])[:1]])
            if cls
            else _note("assembly", "From score to answer", "Assembling a prediction",
                       "To predict, a row walks down EVERY tree; the leaf outputs (times η) "
                       "are summed onto the baseline — and that total IS the prediction.",
                       math=[math_block(m) for m in guide.get("math", [])[:1]])
        ),
    ]
    return _finish("Gradient boosting, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


# ---- linear & regularized -------------------------------------------------------------------


def _linear_core(
    trace: ModelTrace, facts: ModelFacts | None, keys: list[str]
) -> tuple[list[Chapter], dict[str, Any]]:
    guide = explainer_for_chain(keys)
    cls = trace.task == "classification"
    coefs = sorted(trace.coef or [], key=lambda c: -abs(c.get("weight", 0)))
    top = coefs[:3]
    top_txt = ", ".join(f"{c['feature']} {c['weight']:+g}" for c in top) if top else ""
    b = trace.intercept

    chapters = [
        data_chapter(trace),
        _note("weighted-sum", "One score from many columns", "The whole model is a recipe",
              "Every feature gets a learned WEIGHT. Multiply each value by its weight, add "
              "them up (plus an intercept), and you have the score. That's the entire model — "
              "which is exactly why you can read it."
              + (f" Your fitted recipe leads with: {top_txt}." if top_txt else ""),
              math=[_m("The score", "z = b + w₁x₁ + w₂x₂ + …",
                       "Each value times its weight, summed.",
                       [("b", f"intercept — here {b}" if b is not None else "the intercept"),
                        ("wⱼ", "learned weight for feature j"),
                        ("xⱼ", "the row's value for feature j")],
                       f"strongest weights on your data: {top_txt}" if top_txt else "")]),
    ]
    if cls:
        chapters.append(_widget("sigmoid", "The sigmoid squeeze", "Score → probability",
                                "A raw score can be any number; the sigmoid squeezes it into a "
                                "0–1 probability. Watch every held-out row land on this curve "
                                "in the Testing chapter.",
                                "sigmoid-squeeze"))
        chapters.append(_widget("logloss", "Loss = surprise", "What training minimises",
                                "Training punishes CONFIDENT WRONG answers hardest: predicting "
                                "p = 0.95 for a row whose truth is 'no' is a huge surprise — "
                                "and log-loss IS the surprise curve.", "surprise-curve"))
    elif (trace.series or {}).get("regression_fit"):
        chapters.append(chapter(
            "least-squares", "The best-fit line",
            [step("residuals",
                  "Watch the line sweep into your real data. Each point's residual is the vertical "
                  "segment to its predicted point ON the line; least squares minimises the total of "
                  "those gaps SQUARED. Watch the squared-error total fall from the flat "
                  "'predict-the-mean' line to the best fit.",
                  duration_ms=DUR_SHOW, anim=AnimDirective(kind="regression-fit"),
                  math=[_m("Least squares", "min Σ (yᵢ − ŷᵢ)²",
                           "Make the squared misses as small as possible.",
                           [("yᵢ", "the actual point"), ("ŷᵢ", "the predicted point on the line"),
                            ("(·)²", "square, so big misses dominate")], "")])],
            kicker="Least squares, made visible"))
    else:
        chapters.append(_note("least-squares", "The best-fit line", "What 'best' means",
                              "Imagine rubber bands from every point to a candidate line — "
                              "least squares picks the line that minimises the total stretched "
                              "rubber (squared, so big misses hurt extra).",
                              math=[_m("Least squares", "min Σ (yᵢ − ŷᵢ)²",
                                       "Make the squared misses as small as possible.",
                                       [("yᵢ", "truth for row i"), ("ŷᵢ", "the line's prediction")],
                                       "")]))
    chapters.append(_train(
        "descent", "Learning the weights", "Gradient descent, live",
        "Weights start random and roll downhill on the loss surface: nudge each weight in the "
        "direction that reduces the error, repeat. Watch the descent and the weight table "
        "evolve on your data — then drag the hyperparameter knobs to see it re-fit.",
    ))
    if "regularized" in keys:
        alpha = (trace.params or {}).get("alpha") or (trace.params or {}).get("C")
        chapters.append(_note(
            "shrinkage", "The penalty that tames weights", "Ridge, lasso, elastic net",
            "Regularisation adds a price tag to big weights: L2 (ridge) shrinks them all "
            "smoothly; L1 (lasso) drives the useless ones EXACTLY to zero — feature selection "
            "for free; elastic net blends both."
            + (f" Your current penalty setting: {alpha}." if alpha is not None else ""),
            math=[_m("Penalised loss", "loss + α·(‖w‖² or ‖w‖₁)",
                     "The fit now competes against the size of the weights.",
                     [("α", "penalty strength — the overfit dial"),
                      ("‖w‖²", "L2: sum of squared weights (ridge)"),
                      ("‖w‖₁", "L1: sum of absolute weights (lasso)")],
                     "")]))
    return chapters, guide


@register_lesson("logistic_regression")
def logistic_regression_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    """Logistic regression taught as ITS OWN thing — the logit link, the sigmoid, and log-loss —
    NOT 'linear regression with a squashed output'."""
    guide = explainer_for_chain(["linear"])
    coefs = sorted(trace.coef or [], key=lambda c: -abs(c.get("weight", 0)))
    lead = coefs[0] if coefs else None
    b = trace.intercept
    import math as _math

    or_txt = ""
    if lead:
        try:
            or_txt = (f"e^({lead['weight']}) = {round(_math.exp(lead['weight']), 3)}")
        except OverflowError:
            or_txt = ""

    chapters = [
        data_chapter(trace),
        _note("why-not-a-line", "Why not just fit a line?", "The problem logistic solves",
              "The outcome here is YES/NO (0 or 1), not a number. Fit an ordinary straight line "
              "to it and two things break: the line sails BELOW 0 and ABOVE 1, predicting "
              "impossible probabilities, and its errors aren't well-behaved. We need a model "
              "whose output is trapped between 0 and 1. That's the whole reason logistic "
              "regression exists — it is NOT linear regression with a twist.",
              math=[_m("The linear-probability problem", "ŷ = b + Σwx  can be < 0 or > 1",
                       "A straight line isn't bounded, so it predicts nonsense probabilities.",
                       [("ŷ", "the straight-line prediction"), ("0..1", "where a probability must live")],
                       "")]),
        _note("odds-logodds", "Probability → odds → log-odds", "The trick: change the scale",
              "Instead of modelling the probability directly, model its LOG-ODDS. Odds = p/(1−p) "
              "(a 0.8 chance = odds of 4-to-1). Take the log and you get a quantity that ranges "
              "over ALL numbers, −∞ to +∞ — exactly the range a linear score can safely produce. "
              "THAT is what we set equal to the weighted sum.",
              math=[_m("The logit link", "logit(p) = log( p / (1 − p) ) = b + w₁x₁ + w₂x₂ + …",
                       "The LOG-ODDS (not p itself) is the linear part of the model.",
                       [("p", "probability of the positive class"),
                        ("p/(1−p)", "the odds"),
                        ("log(·)", "stretches 0..1 odds onto the whole number line"),
                        ("b, wⱼ", "the learned intercept and weights")],
                       f"your fit's linear score: z = {b} + " + " + ".join(
                           f"{c['weight']}·{c['feature']}" for c in coefs[:2]) if coefs else "")]),
        _widget("weighted-sum-score", "The score, on a real row", "Build z term by term",
                "For one row we compute that linear score z the ordinary way — every feature "
                "times its weight, summed, plus the intercept. So far it looks like linear "
                "regression. The DIFFERENCE is what we do with z next.", "weighted-sum"),
        _widget("sigmoid", "Undo the logit: the sigmoid", "Log-odds → probability",
                "The logit turned probability into a number line; to get a probability BACK we "
                "invert it — and the inverse of the logit IS the sigmoid. It squeezes any z into "
                "(0, 1): big-negative z → near 0, big-positive → near 1, z = 0 → exactly 0.5. "
                "Watch every held-out row land on this S-curve in Testing.", "sigmoid-squeeze",
                math=[_m("The sigmoid (inverse logit)", "p = 1 / (1 + e^(−z))",
                         "Squeezes the linear score into a valid probability.",
                         [("z", "the linear score b + Σwx"), ("p", "probability of the positive class"),
                          ("e", "Euler's number ≈ 2.718")],
                         "z = 0 → p = 0.5 · z = +2 → p ≈ 0.88 · z = −2 → p ≈ 0.12")]),
        _widget("logloss", "Why not squared error? Log-loss", "The right loss for probabilities",
                "Linear regression minimises SQUARED error. Logistic can't — squared error on "
                "probabilities is non-convex and barely punishes confident mistakes. Instead it "
                "minimises LOG-LOSS (cross-entropy): being confidently WRONG (p = 0.95 when the "
                "truth is 0) costs enormously, while a confident correct call costs almost "
                "nothing. It's the 'surprise' of the truth under your prediction.", "surprise-curve",
                math=[_m("Log-loss (binary cross-entropy)",
                         "L = −[ y·log(p) + (1 − y)·log(1 − p) ]",
                         "Punishes confident wrong probabilities hardest; minimised by MLE.",
                         [("y", "the true label (1 or 0)"),
                          ("p", "your predicted probability"),
                          ("−log", "the surprise: rare-under-your-model events cost more")],
                         "truth y=1, p=0.95 → loss 0.05 (tiny) · truth y=1, p=0.05 → loss 3.0 (huge)")]),
        _train("descent", "Learning the weights", "Gradient descent on log-loss",
               "There's no closed-form solution like OLS, so the weights are found by MAXIMUM "
               "LIKELIHOOD via gradient descent: start random, and repeatedly nudge each weight "
               "downhill on the log-loss surface. Watch the loss fall and the weight table settle "
               "on your data; drag the C knob to see regularisation pull the weights toward zero."),
    ]
    if lead and or_txt:
        chapters.append(_note(
            "odds-ratio", "Reading a coefficient: odds ratios", "What the weights MEAN",
            f"A logistic weight lives on the log-odds scale, so exponentiate it to speak human. "
            f"For {lead['feature']}: {or_txt} — each one-unit increase MULTIPLIES the odds of the "
            f"positive outcome by that factor. Above 1 pushes toward yes, below 1 toward no. "
            "(That's a change in ODDS, not probability — the same coefficient moves probability "
            "most near p = 0.5 and least near 0 or 1.)",
            math=[_m("Odds ratio", "OR = e^(wⱼ)",
                     "How the odds multiply per one-unit rise in feature j.",
                     [("wⱼ", "the feature's logit weight"), ("OR", "odds ratio")],
                     f"{lead['feature']}: {or_txt}")]))
    return _finish("Logistic regression, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


@register_lesson("linear_regression")
def linear_regression_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    """Linear regression as REGRESSION — least squares on a numeric outcome. (If the target is
    binary it's a linear probability model, and the note says so.)"""
    guide = explainer_for_chain(["linear"])
    coefs = sorted(trace.coef or [], key=lambda c: -abs(c.get("weight", 0)))
    lead = coefs[0] if coefs else None
    b = trace.intercept
    binary = bool(trace.labels) and len(trace.labels) == 2

    chapters = [
        data_chapter(trace),
        _note("best-fit-line", "The best-fit line", "One line through the cloud",
              "Linear regression draws the straight line (in many dimensions, a plane) that "
              "sits as close as possible to every point. Each feature gets a slope — a per-unit "
              "effect on the outcome number."
              + (" Your target here is 0/1, so this is a LINEAR PROBABILITY MODEL: the same line, "
                 "read as a probability (it can stray outside 0–1 — that's its known flaw)."
                 if binary else ""),
              math=[_m("The model", "ŷ = b + w₁x₁ + w₂x₂ + …",
                       "Prediction = intercept plus each feature times its slope.",
                       [("ŷ", "the predicted number"), ("b", f"intercept — here {b}"),
                        ("wⱼ", "slope for feature j (its per-unit effect)")],
                       f"leading effect: {lead['feature']} moves the outcome by {lead['weight']} "
                       f"per unit" if lead else "")]),
        chapter("audition", "What makes a line 'best'?",
                [step("residuals",
                      "Watch the line sweep into your real data. Every point's RESIDUAL is the "
                      "vertical segment linking it to its predicted point ON the line. Least "
                      "squares picks the line that makes the total of those gaps, SQUARED, as "
                      "small as possible — squaring means big misses hurt far more, and it gives "
                      "one clean closed-form answer. Watch the squared-error total shrink from the "
                      "flat 'just predict the mean' line down to the best fit.",
                      duration_ms=DUR_SHOW, anim=AnimDirective(kind="regression-fit"),
                      math=[_m("Least squares", "minimise  Σ (yᵢ − ŷᵢ)²",
                               "Make the summed squared residuals as small as possible.",
                               [("yᵢ", "the true value (the actual point)"),
                                ("ŷᵢ", "the predicted point on the line"),
                                ("yᵢ − ŷᵢ", "the residual — the red segment"),
                                ("(·)²", "square, so big misses dominate")],
                               "solved in closed form by the normal equations — no iteration needed")])],
                kicker="Least squares, made visible"),
        _note("coefficients", "Reading the coefficients", "Per-unit effects you can quote",
              "Each weight is a marginal effect: hold everything else fixed, raise this feature "
              "by one unit, and the prediction moves by exactly that weight. That plain-English "
              "readability is why linear regression is the baseline every field trusts."
              + (f" On your data, {lead['feature']} carries the biggest effect ({lead['weight']} "
                 "per unit)." if lead else "")),
        _note("r2", "How good is the fit? R²", "Variance explained",
              "R² is the share of the outcome's variance the line explains: 0 = no better than "
              "predicting the mean, 1 = every point on the line. Watch out — adding ANY feature "
              "never lowers R², so compare with adjusted R² or out-of-sample error."),
    ]
    return _finish("Linear regression, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


@register_lesson("linear")
def linear_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    chapters, guide = _linear_core(trace, facts, ["linear"])
    return _finish("Linear models, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


@register_lesson("regularized")
def regularized_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    chapters, guide = _linear_core(trace, facts, ["regularized", "linear"])
    return _finish("Regularised regression, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


# ---- neural network --------------------------------------------------------------------------


@register_lesson("nn")
def nn_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["nn"])
    key = facts.key if facts else "mlp"
    layers = trace.layers or []
    arch = " → ".join(str(n) for n in layers) if layers else "input → hidden → output"
    series = trace.series or {}
    lc = series.get("loss_curve") or []
    loss_txt = (f"watch the loss fall from {lc[0]} to {lc[-1]}" if len(lc) > 1
                else "watch the loss fall")

    chapters = [
        data_chapter(trace),
        _note("neuron", "One neuron", "The atom of every network",
              "A neuron is just the linear recipe you already know — weighted sum plus bias — "
              "followed by a squash (the activation). ReLU keeps positives and zeroes the "
              "rest; sigmoid squeezes to 0–1; tanh to −1…1. Stack neurons and the squashes "
              "are what let the network BEND.",
              math=[_m("A neuron", "a = f(b + Σ wⱼxⱼ)", "Weighted sum, then a squash.",
                       [("f", "the activation (ReLU/sigmoid/tanh)"),
                        ("wⱼ, b", "learned weights and bias")],
                       "ReLU(−2.3) = 0 · ReLU(1.7) = 1.7 — negatives are silenced")]),
        _train("network", "Your network, live", "Forward pass",
               f"This is the real network fitted on your data — architecture {arch}. Edge "
               "thickness and colour are the LEARNED weights (green +, red −). Watch a row's "
               "values pulse forward through the layers into a prediction."),
        _train("backprop", "Backpropagation", "Blame flows backwards",
               "Compare the output to the truth → that's the loss. Then the chain rule sends "
               "BLAME backwards through the same wires: every weight learns how much IT "
               "contributed to the miss, and steps the other way. Forward, error, backward, "
               f"step — thousands of times; {loss_txt} in the curve below the network.",
               math=[_m("The update", "w ← w − lr · ∂loss/∂w",
                        "Each weight steps against its own share of the blame.",
                        [("lr", "learning rate — step size"),
                         ("∂loss/∂w", "this weight's blame, via the chain rule")],
                        "")]),
    ]

    # the optimizer RACE — three real fits of the same net, three real loss curves
    opts = series.get("optimizers") or {}
    if len(opts) >= 2:
        chapters.append(chapter(
            "optimizer-race", "The optimizer race",
            [step(
                "race",
                "Same network, same data, three rolling styles — these are three REAL training "
                "runs: plain SGD steps straight downhill and can zig-zag; MOMENTUM remembers "
                "its velocity and barrels through ravines; ADAM adapts the step size per "
                "weight, today's default. Watch whose loss curve wins on your data.",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="optimizer-race",
                                   substeps=max(len(v) for v in opts.values())),
            )],
            kicker="SGD vs momentum vs Adam — real curves, your data"))
    else:
        chapters.append(_widget(
            "descent", "Gradient descent's family", "SGD, momentum, Adam",
            "Plain SGD steps straight downhill and can zig-zag; momentum remembers its "
            "velocity and barrels through ravines; Adam adapts the step size per weight — "
            "today's default. Same bowl, different rolling styles.", "hessian-bowl"))

    # ---- model-specific machinery, computed on YOUR data --------------------------------
    conv = series.get("conv") or {}
    if key == "cnn" and conv.get("grid"):
        n = len(conv["fmap"])
        chapters.append(chapter(
            "convolution", "Convolution: the sliding detector",
            [step(
                "conv-slide",
                "Your row's values, arranged as a grid. The little 2×2 kernel is a vertical-"
                "edge detector; it SLIDES across the grid and, at every position, multiplies "
                "cell-by-cell and adds up — one number per stop, filling the feature map. One "
                "detector, reused everywhere: that's why CNNs learn a pattern once and find "
                "it anywhere.",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="conv-slide", substeps=n * n),
                math=[_m("The convolution at one stop", "out = Σ (patch ⊙ kernel)",
                         "Element-wise multiply the window by the kernel, then sum.",
                         [("patch", "the 2×2 slice of the grid under the kernel"),
                          ("⊙", "multiply matching cells"),
                          ("kernel", "the learned detector (here: a vertical-edge probe)")],
                         "")],
            )],
            kicker="One detector, every position"))
        pn = len(conv.get("pooled") or [1])
        chapters.append(chapter(
            "pooling", "Max-pooling: keep the strongest evidence",
            [step(
                "max-pool",
                "After ReLU zeroes the negatives, a 2×2 window slides over the feature map "
                "and only the MAX survives each stop. The map shrinks, tiny shifts stop "
                "mattering, and the strongest evidence is what moves forward. That's the whole "
                "trick: detect everywhere, keep the loudest.",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="max-pool", substeps=pn * pn),
            )],
            kicker="Shrink the picture, keep the signal"))
    lstm = series.get("lstm") or {}
    if key in ("rnn", "lstm", "gru") and lstm.get("steps"):
        chapters.append(_note(
            "unroll", "Reading step by step", "Why plain RNNs forget",
            "A recurrent net is ONE cell applied again and again along the sequence, passing a "
            "hidden state forward like a baton. Training sends gradients backwards through "
            "every step — and multiplying many small numbers fades them to nothing. Long "
            "memories die. The LSTM's fix: a protected cell state with GATES."))
        chapters.append(chapter(
            "lstm-gates", "The LSTM cell, gate by gate",
            [step(
                "gates",
                "This is a real LSTM cell trained on your data, replayed one timestep at a "
                "time. The conveyor on top is the CELL STATE (the memory). At every step the "
                "three dials are its learned gates: FORGET (how much memory to keep), INPUT "
                "(how much new information to write), OUTPUT (how much memory to reveal). GRU "
                "is the leaner 2-gate sibling of exactly this machine.",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="lstm-gates", substeps=len(lstm["steps"])),
                math=[_m("The cell update", "c_t = f·c_(t−1) + i·g",
                         "New memory = kept old memory + gated new candidate.",
                         [("f", "forget gate (0 = wipe, 1 = keep)"),
                          ("i", "input gate (0 = ignore, 1 = write)"),
                          ("g", "the candidate new content"),
                          ("c_t", "the cell state — the conveyor belt")],
                         "")],
            )],
            kicker="Forget · input · output — live dials"))

    chapters.append(_note(
        "epochs", "Watch it improve", "Same row, different epochs",
        "In the training view, the epoch cards show the SAME row's prediction drifting "
        "toward the truth as the epochs tick by — that's the whole loop, made visible. "
        "CNNs slide this machinery over grids; LSTMs run it along sequences with gates; "
        "transformers wire it with attention — same forward/backward heartbeat."))
    return _finish("Neural networks, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


# ---- knn --------------------------------------------------------------------------------------


@register_lesson("knn")
def knn_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["knn"])
    k = (trace.series or {}).get("k", 5)
    fx, fy = (trace.series or {}).get("x"), (trace.series or {}).get("y")

    chapters = [
        data_chapter(trace),
        _note("memorize", "No training. Really.", "The laziest good model",
              "k-NN never fits anything — it just MEMORISES every training row. All the work "
              "happens at prediction time: find the k most similar remembered rows and let "
              "them vote (or average). The map you'll see plots your rows by "
              + (f"{fx} and {fy}, its two most telling features." if fx and fy
                 else "their two most telling features.")),
        _train("distance", "Similar = close", "The distance ruler",
               f"Similarity is plain geometric distance. For a new row, measure the distance "
               f"to every remembered row, sort, and keep the k = {k} closest. One warning: "
               "features on big scales hog the ruler — always scale first.",
               math=[_m("Euclidean distance", "d = √((x₁−x₁′)² + (x₂−x₂′)² + …)",
                        "The straight-line distance between two rows.",
                        [("x, x′", "the new row and a remembered row")],
                        "rows (5, 120) and (8, 118): d = √(9 + 4) = √13 ≈ 3.6")]),
        _note("vote", "The neighbourhood votes", "k decides the flavour",
              f"With k = {k}, the {k} nearest rows each cast a vote"
              + (" and the majority label wins."
                 if trace.task == "classification" else " and their average is the prediction.")
              + " Small k = flexible but jumpy (one noisy neighbour can flip you); big k = "
              "smooth but blurry. In Testing, watch the neighbours light up one by one."),
    ]
    return _finish("k-nearest neighbours, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


# ---- clustering --------------------------------------------------------------------------------


_CLUSTER_MECH: dict[str, tuple[str, str, str, str]] = {
    "dbscan": ("dbscan-grow", "DBSCAN's own move: density chain-reactions",
               "The mechanism you chose",
               "DBSCAN never picks k. Draw an ε-radius circle around each point; a point with "
               "enough neighbours is a CORE point, and it ignites: everything within ε joins, "
               "and every core it touches chain-reacts onward. Clusters take ANY shape the "
               "density carves, and loners are honestly stamped noise instead of being forced "
               "into a group."),
    "gmm": ("gmm-ellipses", "GMM's own move: soft membership by EM",
            "The mechanism you chose",
            "A gaussian mixture never makes hard assignments. E-step: every point receives "
            "RESPONSIBILITIES — 60% blue, 40% green. M-step: each ellipse re-centres, "
            "re-shapes and re-tilts using those weighted votes. Repeat; the log-likelihood can "
            "only climb. K-means is exactly this machine with round ellipses and all-or-nothing "
            "votes."),
    "hierarchical": ("dendro-zip", "Hierarchical's own move: zip and record",
                     "The mechanism you chose",
                     "Every point starts as its own cluster. Find the closest pair, zip them "
                     "together, record HOW FAR APART they were as the bracket's height, and "
                     "repeat until one tree remains. The dendrogram IS the output: slide a cut "
                     "line across it and any number of clusters falls out — no k chosen in "
                     "advance."),
    "spectral": ("spectral-jump", "Spectral's own move: the embedding jump",
                 "The mechanism you chose",
                 "Build a similarity graph over the points, then use the graph Laplacian's "
                 "leading eigenvectors as NEW coordinates. Weakly-connected groups land far "
                 "apart in that space — a ring inside a ring becomes two plain blobs — and "
                 "ordinary k-means finishes the job up there."),
}


@register_lesson("clustering")
def clustering_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["clustering"])
    key = facts.key if facts else "kmeans"
    s = trace.series or {}
    k = s.get("k")
    iters = s.get("iterations") or []
    inertia_txt = ""
    if len(iters) > 1:
        first, last = iters[0].get("inertia"), iters[-1].get("inertia")
        if first is not None and last is not None:
            inertia_txt = (f" On your data the total spread fell from {first} to {last} in "
                           f"{len(iters)} rounds.")

    chapters = [
        data_chapter(trace),
        _note("no-teacher", "Learning without answers", "Unsupervised",
              "There is no outcome column here — the model's job is to DISCOVER structure: "
              "groups of rows that belong together. 'Together' means close in feature space, "
              "so scaling matters as much as it did for k-NN."),
    ]
    mech = _CLUSTER_MECH.get(key)
    if mech:
        widget_key, title, kicker, narration = mech
        # if the tracer computed the REAL per-algorithm structure on this data, animate THAT;
        # otherwise fall back to the illustrative concept widget.
        real = s.get("mechanism") or {}
        real_stage = {
            "dbscan": ("dbscan-real", len(real.get("points") or []) or real.get("total_steps", 1)),
            "gmm": ("gmm-real", len(real.get("points") or [1])),
            "hierarchical": ("dendrogram-real", len(real.get("merges") or [1])),
            "spectral": ("spectral-real", 20),
        }
        if real.get("kind") == key and key in real_stage:
            kind, substeps = real_stage[key]
            chapters.append(chapter(
                f"{key}-mechanism", title,
                [step(f"{key}-mech", narration + " Every point below is YOUR data.",
                      duration_ms=DUR_SHOW,
                      anim=AnimDirective(kind=kind, substeps=max(1, substeps)))],
                kicker=kicker))
        else:
            chapters.append(_widget(f"{key}-mechanism", title, kicker, narration, widget_key))
    chapters.append(_train(
        "loop", "The canonical loop (k-means)", "Assign, then move",
        ("K-means" + (f" with k = {k}" if k else "") + ": "
         if not mech
         else "For contrast, here is clustering's canonical loop — k-means, fitted live on "
         "your data (your chosen algorithm's own move is above): ")
        + "drop the centres, then loop two moves — ASSIGN every point to its nearest "
        "centre, then MOVE each centre to the mean of its members. Repeat until nothing "
        "changes. Use the ◀ ▶ transport under the map to step through the real "
        f"iterations.{inertia_txt}",
        math=[_m("Inertia — the score being minimised",
                 "inertia = Σ ‖xᵢ − c(xᵢ)‖²",
                 "Total squared distance from each point to its centre.",
                 [("xᵢ", "a data point"), ("c(xᵢ)", "the centre it's assigned to")],
                 inertia_txt.strip() or "each iteration can only lower it")]))
    chapters.append(_note(
        "siblings", "The same idea, different rules", "DBSCAN · GMM · hierarchical · spectral",
        "Every clustering algorithm answers 'what counts as together?' differently: "
        "DBSCAN grows clusters through dense neighbourhoods (any shape, flags noise); "
        "gaussian mixtures give SOFT memberships with elliptical clusters; hierarchical "
        "zips the closest pairs into a dendrogram you can cut at any height; spectral "
        "cuts the weakest links of a similarity graph. The verdict chapter says when "
        "each wins."))
    return _finish("Clustering, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


# ---- anomaly -----------------------------------------------------------------------------------


_ANOMALY_MECH: dict[str, tuple[str, str, str]] = {
    "isolation_forest": ("isolation-cuts", "Isolation Forest's own move: random cuts",
                         "Weird points are easy to fence off: slice the space with RANDOM cuts. "
                         "A lonely point is boxed in after two or three slices; a point deep in "
                         "the crowd needs many. Average the path lengths over many random trees "
                         "— short average path = anomalous. No distances, no densities, just "
                         "cuts, which is why it scales."),
    "lof": ("density-rings", "LOF's own move: compare neighbourhoods",
            "LOF asks a LOCAL question: am I less crowded than MY OWN neighbours are? Each "
            "point measures the ring it needs to reach k neighbours; divide your neighbours' "
            "density by yours. A point that's ordinary globally but sparse for its "
            "neighbourhood — odd for its suburb — scores LOF ≫ 1 and gets caught where global "
            "methods miss it."),
    "one_class_svm": ("shrink-wrap", "One-Class SVM's own move: the shrink-wrap",
                      "Learn a boundary around NORMAL and flag whatever falls outside. The "
                      "wrap is a kernel boundary tightened around the training cloud; ν sets "
                      "how many training points may be left outside (the looseness). The "
                      "catch: the training data must be clean — anomalies inside the wrap "
                      "poison it."),
}


@register_lesson("anomaly")
def anomaly_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["anomaly"])
    key = facts.key if facts else "isolation_forest"
    s = trace.series or {}
    n_anom, n_train = s.get("n_anomalies"), s.get("n_train")
    found = (f" On your data it flagged {n_anom} of {n_train} rows."
             if n_anom is not None and n_train else "")
    widget_key, mech_title, mech_narr = _ANOMALY_MECH.get(key, _ANOMALY_MECH["isolation_forest"])

    # prefer the REAL per-algorithm mechanism computed on this data; else the concept widget
    real = (trace.series or {}).get("mechanism") or {}
    real_stage = {
        "isolation_forest": ("iforest-real", len(real.get("hist") or [1])),
        "lof": ("lof-real", len((real.get("focus") or {}).get("neighbors") or [1])),
        "one_class_svm": ("ocsvm-real", 1),
    }
    if real.get("kind") == key and key in real_stage:
        rkind, rsub = real_stage[key]
        mech_chapter = chapter(
            f"{key}-mechanism", mech_title,
            [step(f"{key}-mech", mech_narr + " Every point below is YOUR data.",
                  duration_ms=DUR_SHOW, anim=AnimDirective(kind=rkind, substeps=max(1, rsub)))],
            kicker="The mechanism you chose")
    else:
        mech_chapter = _widget(f"{key}-mechanism", mech_title, "The mechanism you chose",
                               mech_narr, widget_key)

    chapters = [
        data_chapter(trace),
        _note("weird", "What makes a row 'weird'?", "Unsupervised again",
              "No labels — the model learns what USUAL looks like and scores every row by how "
              "badly it fits that picture." + found),
        mech_chapter,
        _train("scores", "Scores and the threshold", "Where the alarm rings",
               "Every row gets an anomaly score; a threshold turns scores into alarms. The "
               "contamination knob IS that threshold — it encodes the business question 'what "
               "share of rows do we expect to be bad?'. Watch each held-out row's score land "
               "left or right of the line in Testing.",
               math=[_m("Isolation score", "score ≈ 2^(−E[h(x)]/c(n))",
                        "Shorter average isolation paths → score closer to 1 (anomalous).",
                        [("E[h(x)]", "average cuts needed to isolate row x"),
                         ("c(n)", "the typical path length for n rows — a normaliser")],
                        "")]),
        _note("siblings", "Three lenses on 'unusual'", "iForest · LOF · one-class SVM",
              "Isolation forest asks 'how easy are you to fence off?' (global, fast). LOF asks "
              "'are you less crowded than YOUR neighbours?' (local). One-class SVM shrink-wraps "
              "a boundary around normal and flags whatever falls outside (needs clean normals). "
              "The verdict chapter picks between them."),
    ]
    return _finish("Anomaly detection, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


# ---- timeseries --------------------------------------------------------------------------------


@register_lesson("timeseries")
def timeseries_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["timeseries"])
    coef = ((trace.series or {}).get("coef") or {})
    phi = coef.get("phi") or []
    c0 = coef.get("c")
    phi_txt = ", ".join(f"φ{i + 1} = {p}" for i, p in enumerate(phi[:3]))

    key = facts.key if facts else "arima"
    chapters = [
        data_chapter(trace),
        (
            _widget("decompose", "Peel the series apart", "ETS's own move",
                    "One tangled line is really three: a LEVEL (where we are), a TREND (where "
                    "we're drifting) and a SEASON (the rhythm that repeats). ETS maintains each "
                    "with exponentially fading memory — α, β and γ set how fast each forgets — "
                    "then re-adds them forward to forecast.", "decompose-stack")
            if key == "ets"
            else _widget("stationarity", "Make it stationary first", "Differencing — the d in ARIMA",
                         "AR and MA machinery assume the series' behaviour doesn't drift. Real "
                         "series drift. The fix is DIFFERENCING: model the CHANGES, value(t) − "
                         "value(t−1), instead of the levels — one subtraction and the trend is "
                         "gone. That's the d in ARIMA; SARIMA applies the same trick at the "
                         "seasonal lag (this January minus last January).", "differencing")
        ),
        _note("lag-window", "The past predicts the future", "Autoregression",
              "A time series' best predictor is usually ITSELF, a few steps ago. An AR model "
              "slides a window over the history: today ≈ a constant plus weighted copies of "
              "the last few values. Those weights are learned like any regression."
              + (f" Yours came out: {phi_txt}." if phi_txt else ""),
              math=[_m("AR(p)", "value(t) = c + φ₁·value(t−1) + … + φₚ·value(t−p)",
                       "Today is a weighted echo of the recent past.",
                       [("c", f"the constant — here {c0}" if c0 is not None else "the constant"),
                        ("φᵢ", "how loudly lag i echoes"),
                        ("p", "how far back the window reaches")],
                       f"your fit: value(t) ≈ {c0} + " + " + ".join(
                           f"{p}·value(t−{i + 1})" for i, p in enumerate(phi[:3]))
                       if phi else "")]),
        _train("fit", "The fit over your history", "Fitted vs actual",
               "The chart overlays the model's fitted line on the real series; the gold band "
               "is the held-out end it never saw. In Testing, step through each forecast and "
               "watch the lag window slide — every prediction is just the window's values "
               "times the φ weights."),
        _note("family", "The ARIMA family tree", "d, q, and seasons",
              "Real series drift and cycle, so the family adds tools: DIFFERENCING (the d in "
              "ARIMA) subtracts yesterday to flatten trends; MA terms (q) let yesterday's "
              "ERRORS nudge today; SARIMA adds the same machinery at the seasonal lag (last "
              "January predicts this January); ETS instead maintains level/trend/season with "
              "fading memory. The verdict chapter picks between them."),
    ]
    return _finish("Forecasting, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


# ---- transformer -------------------------------------------------------------------------------


@register_lesson("var")
def var_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["timeseries"])
    chapters = [
        data_chapter(trace),
        _note("joint", "Series that move together", "Why one equation isn't enough",
              "GDP, inflation and interest rates don't evolve alone — each depends on the recent "
              "past of ALL of them. A VAR writes one autoregression PER series, with every "
              "series' lags on the right-hand side, and estimates them jointly.",
              math=[_m("A 2-variable VAR(1)",
                       "yₜ = a₁ + b₁·y_(t−1) + c₁·x_(t−1) + e\nxₜ = a₂ + b₂·y_(t−1) + c₂·x_(t−1) + u",
                       "Each series is regressed on the last period of every series.",
                       [("y, x", "the interrelated series"),
                        ("b, c", "how each series' past feeds each equation")],
                       "")]),
        _train("dynamics", "Fitting the joint dynamics", "On your series",
               "The staged view fits the autoregressive structure on your data. The real power "
               "of a VAR is what you compute AFTER fitting: impulse responses and Granger tests."),
        _note("impulse", "The impulse-response function", "What people actually read",
              "Shock one series by one unit and trace how EVERY series responds over the next "
              "periods, holding the estimated dynamics fixed. That path — 'a rate hike lowers "
              "inflation after ~4 quarters' — is the headline output of any VAR, and the basis "
              "of Granger causality: does X's past help predict Y beyond Y's own past?"),
    ]
    return _finish("Vector autoregression, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


@register_lesson("transformer")
def transformer_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["transformer"])
    s = trace.series or {}
    heads, d_model = s.get("heads"), s.get("d_model")
    k = len(trace.features)

    chapters = [
        data_chapter(trace),
        _note("tokens", "Everything becomes a token", "Features as a sequence",
              f"Your {k} feature columns are embedded as TOKENS — little learned vectors"
              + (f" of size {d_model}" if d_model else "")
              + ". The transformer's one move: let every token look at every other token and "
              "decide how much to LISTEN. No loops, no sliding windows — everyone sees "
              "everyone, in parallel."),
        _note("qkv", "Queries, keys, values", "How 'listening' is computed",
              "Each token asks a question (its Query), advertises what it offers (its Key), "
              "and carries content (its Value). Attention = match every Q against every K, "
              "softmax the scores into weights that sum to 1, then blend the Vs. Rows that "
              "matter to you get louder; the rest fade.",
              math=[_m("Scaled dot-product attention",
                       "attention = softmax(Q·Kᵀ/√d)·V",
                       "Match questions to offers, then blend the content.",
                       [("Q, K, V", "query/key/value vectors, all learned"),
                        ("√d", "a scale factor that keeps softmax gentle"),
                        ("softmax", "turns scores into weights that sum to 1")],
                       "")]),
        _train("heatmap", "Attention on your data", "Watch it sharpen",
               ("The heatmap shows who-listens-to-whom across your features"
                + (f", one tab per head ({heads} heads learn {heads} different listening "
                   f"patterns)" if heads else "")
                + ". Flip the stage tabs — untrained attention is a uniform blur; training "
                "carves it into structure. BERT, GPT and ViT run exactly this mechanism, "
                "thousands of times wider.")),
    ]
    return _finish("Transformers, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


# ---- panel data (pooled OLS · fixed effects · random effects) --------------------------------


@register_lesson("panel")
def panel_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["linear"])
    name = facts.display_name if facts else "panel regression"
    key = facts.key if facts else "pooled_ols"
    inf = ((trace.series or {}).get("inference") or {})
    rows = [r for r in inf.get("rows", []) if r.get("feature") != "intercept"]

    chapters: list[Chapter] = [data_chapter(trace)]
    chapters.append(_note(
        "panel-story", "The same entities, again and again", "What makes data 'panel'",
        "Panel data follows the SAME entities (people, firms, states) across periods. That "
        "repetition is a gift: each entity can act as its own control. It's also a trap: rows "
        "of the same entity are related, and every entity carries invisible, time-constant "
        "baggage (culture, talent, geography) that a naive regression silently absorbs into "
        "the wrong coefficient."))
    chapters.append(_widget(
        "demeaning", "Watch the confounder vanish", "The within transform, animated",
        "Each colour is one entity. The POOLED line chases the differences BETWEEN entities — "
        "which is exactly where the invisible baggage lives. Now subtract each entity's own "
        "averages: the groups slide onto a common centre, the between-entity story is erased, "
        "and the line re-fits on WITHIN-entity changes only. That re-fitted slope is the "
        "fixed-effects estimate.",
        "fe-demean",
        math=[_m("The within transform",
                 "yᵢₜ − ȳᵢ = β(xᵢₜ − x̄ᵢ) + (εᵢₜ − ε̄ᵢ)",
                 "Subtract each entity's own means — the entity effect αᵢ cancels exactly.",
                 [("αᵢ", "entity i's time-constant baggage (cancels!)"),
                  ("ȳᵢ, x̄ᵢ", "entity i's own averages"),
                  ("β", "identified from WITHIN-entity changes only")],
                 "")]))
    chapters.append(_note(
        "three-estimators", "Pooled vs fixed vs random", "The panel ladder",
        ("You are watching POOLED OLS: one regression over all stacked rows — fine as a "
         "baseline, but cluster the standard errors and fear entity-level confounders. "
         if key == "pooled_ols" else
         "You are watching FIXED EFFECTS: the demeaned regression from the animation — the "
         "causal workhorse, at the price of losing all between-entity information. "
         if key == "fixed_effects" else
         "You are watching RANDOM EFFECTS: entity intercepts treated as random draws — a "
         "weighted blend of within and between variation, more efficient than FE but only "
         "honest if the entity effects are uncorrelated with the regressors. ")
        + "The ladder: report pooled as the baseline → prefer FE when entities carry baggage "
        "→ switch to RE only when the Hausman test says FE and RE agree."))
    if rows:
        chapters.append(chapter(
            "inference-table", "The inference table",
            [step(
                "inference",
                f"The fitted coefficients on your data ({inf.get('n')} rows), each with its "
                "standard error, test statistic, p-value and confidence interval — read them "
                "exactly as in OLS, but remember: with panel rows the honest version clusters "
                "the errors by entity.",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="inference-table", substeps=max(1, len(rows))),
            )],
            kicker="SE · t · p · CI on your fit"))
    return _finish(f"{name}: the panel story", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


# ---- causal inference (RCT · DiD · IV) -------------------------------------------------------


@register_lesson("causal")
def causal_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["linear"])
    m = (trace.series or {}).get("mechanism") or {}
    kind = m.get("kind", "rct")
    name = facts.display_name if facts else "causal inference"

    chapters = [
        _note("prediction-vs-cause", "Prediction is not causation", "The whole point",
              "Every model so far answered 'what will Y be?'. Causal inference answers a harder "
              "question: 'if we INTERVENE and change X, how does Y change?' Correlation is "
              "everywhere; causation needs an identification strategy — a reason the comparison "
              "is fair. Here's how this one earns it, estimated for real on a classic design.")
    ]

    if kind == "rct" and m:
        chapters.append(chapter(
            "rct", "Randomisation makes it fair",
            [step("rct-scene",
                  f"A job-training RCT: {m['n_treated']} people were RANDOMLY offered training, "
                  f"{m['n_control']} were not. Because a coin flip decided who got it, the two "
                  "groups are alike in everything else — ability, motivation, luck — so the gap "
                  "in their average earnings IS the causal effect. Watch the two clouds and their "
                  "means.",
                  duration_ms=DUR_SHOW,
                  anim=AnimDirective(kind="rct-real", substeps=max(1, len(m.get("treated_pts") or [1]))),
                  math=[_m("The estimator", "ATE = ȳ(treated) − ȳ(control)",
                           "A difference in group means — nothing fancier is needed.",
                           [("ȳ", "a group's average outcome"),
                            ("ATE", "average treatment effect")],
                           f"{m['treated_mean']} − {m['control_mean']} = {m['ate']} "
                           f"(true effect {m['true_effect']}; 95% CI [{m['ci_low']}, {m['ci_high']}])")])],
            kicker="A difference in means — but earned by design"))
    elif kind == "did" and m:
        chapters.append(chapter(
            "did", "Difference-in-Differences",
            [step("did-scene",
                  "A minimum-wage study: one state raised its wage (treated), a neighbour didn't "
                  "(control). We can't just compare after — the states differ. And we can't just "
                  "look at the treated state's before→after — the economy moved anyway. DiD does "
                  "BOTH subtractions: the treated change minus the control change removes the "
                  "fixed gap AND the common trend.",
                  duration_ms=DUR_SHOW,
                  anim=AnimDirective(kind="did-real", substeps=4),
                  math=[_m("The DiD estimator",
                           "effect = (T_post − T_pre) − (C_post − C_pre)",
                           "The treated group's jump, minus the jump that would've happened anyway.",
                           [("T", "treated group mean"), ("C", "control group mean"),
                            ("pre/post", "before / after the policy")],
                           f"({m['treated_post']} − {m['treated_pre']}) − "
                           f"({m['control_post']} − {m['control_pre']}) = {m['did_effect']} "
                           f"(true {m['true_effect']})")])],
            kicker="Subtract the trend, keep the treatment"))
        chapters.append(_note(
            "parallel-trends", "The load-bearing assumption", "Parallel trends",
            "DiD is only causal if, WITHOUT the policy, the two groups would have moved in "
            "parallel. That's untestable after the fact — so honest studies plot the "
            "pre-treatment trends and show they tracked each other before diverging."))
    elif kind == "iv" and m:
        chapters.append(_note(
            "endogeneity", "The problem: a hidden confounder", "Why plain OLS lies",
            "Does an extra year of schooling raise wages? Regress wages on schooling and you get "
            f"{m['naive_ols_effect']} — but ABILITY raises both schooling and wages, so that "
            "number is contaminated. Schooling is 'endogenous': correlated with the error. We "
            "need variation in schooling that has nothing to do with ability."))
        chapters.append(chapter(
            "iv", "The instrument, in two stages",
            [step("iv-scene",
                  "The instrument: growing up NEAR a college nudges schooling but doesn't touch "
                  "wages directly. Stage 1 regresses schooling on the instrument to isolate the "
                  "clean, ability-free part of schooling. Stage 2 regresses wages on THAT — and "
                  "the coefficient is finally causal.",
                  duration_ms=DUR_SHOW,
                  anim=AnimDirective(kind="iv-real", substeps=3),
                  math=[_m("Two-stage least squares",
                           "① X̂ = a + b·Z   ② Y = c + β·X̂",
                           "Predict the endogenous X from the instrument Z, then use only that part.",
                           [("Z", "the instrument (near-college)"),
                            ("X̂", "the instrument-driven part of schooling"),
                            ("β", "the causal return to schooling")],
                           f"IV effect = {m['iv_effect']} (true {m['true_effect']}) vs "
                           f"confounded OLS {m['naive_ols_effect']}; first-stage F = "
                           f"{m['first_stage_F']}")])],
            kicker="Clean the regressor, then regress"))
        chapters.append(_note(
            "weak-iv", "When it breaks", "Weak instruments & LATE",
            "If the instrument barely moves X (first-stage F < 10) the estimate collapses back "
            "toward the biased OLS and gets noisy. And IV recovers a LOCAL effect — for the "
            "'compliers' the instrument actually swayed — not the average for everyone."))

    elif kind == "rdd" and m:
        chapters.append(_note(
            "cutoff", "A rule creates the experiment", "Assignment by threshold",
            "Sometimes treatment is assigned by a RULE: score ≥ cutoff gets the scholarship, "
            "below doesn't. Someone at 79 and someone at 81 are basically identical — luck of a "
            "point decides treatment. So the JUMP in the outcome exactly at the cutoff is as good "
            "as random."))
        chapters.append(chapter(
            "rdd", "The jump at the cutoff",
            [step("rdd-scene",
                  "Fit a line on each side of the cutoff. Everything else is continuous there, so "
                  "the vertical GAP between the two lines at the threshold is the causal effect — "
                  "no confounder can jump discontinuously at an arbitrary score.",
                  duration_ms=DUR_SHOW,
                  anim=AnimDirective(kind="rdd-real",
                                     substeps=max(1, len(m.get("left") or [])
                                                  + len(m.get("right") or []))),
                  math=[_m("The RD estimate",
                           "effect = lim(r↓c) E[Y] − lim(r↑c) E[Y]",
                           "The gap between the just-above and just-below outcome, at the cutoff c.",
                           [("r", "the running variable (the score)"),
                            ("c", "the cutoff"),
                            ("Y", "the outcome")],
                           f"jump = {m['jump_hi']} − {m['jump_lo']} = {m['rd_effect']} "
                           f"(true {m['true_effect']})")])],
            kicker="Two local lines, one gap"))
        chapters.append(_note(
            "rdd-caveats", "What to check", "Local & manipulable",
            "RDD's effect is LOCAL to the cutoff — it may not generalise far from it. And if "
            "people can MANIPULATE their score to land just above (bunching), the design breaks; "
            "honest studies show the density is smooth through the cutoff."))

    tail = [verdict_chapter(facts, guide, name)]
    quiz = quiz_chapter(facts, name)
    if quiz:
        tail.append(quiz)
    full = [*chapters, *tail]
    return [roadmap_chapter(f"{name}: proving cause, not correlation",
                            full, str(guide.get("one_liner", ""))), *full]


# ---- volatility (ARCH · GARCH) ---------------------------------------------------------------


@register_lesson("volatility")
def volatility_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["timeseries"])
    m = (trace.series or {}).get("mechanism") or {}
    kind = m.get("kind", "garch")
    name = facts.display_name if facts else ("GARCH" if kind == "garch" else "ARCH")

    chapters: list[Chapter] = [data_chapter(trace)]
    chapters.append(_note(
        "clustering", "Volatility clusters", "The one fact that matters",
        "Look at any financial return series: the LEVEL is nearly unpredictable, but the SIZE of "
        "moves is not. Calm days follow calm days; wild days follow wild days. That clustering is "
        "what ARCH/GARCH model — not where the price goes, but how uncertain we are about it."))
    if m:
        chapters.append(chapter(
            "vol-path", f"{name} on your series",
            [step("vol-scene",
                  "Here is your real series as shocks, with the model's CONDITIONAL VOLATILITY "
                  "riding underneath — it swells inside turbulent stretches and settles in calm "
                  "ones, computed from the fitted parameters. That band is a live risk forecast.",
                  duration_ms=DUR_SHOW,
                  anim=AnimDirective(kind="volatility-real",
                                     substeps=max(1, len(m.get("vol") or [1]))),
                  math=[_m(
                      "GARCH(1,1) variance" if kind == "garch" else "ARCH(1) variance",
                      "σ²_t = ω + α·ε²_(t−1) + β·σ²_(t−1)" if kind == "garch"
                      else "σ²_t = ω + α·ε²_(t−1)",
                      "Today's variance = baseline + reaction to yesterday's shock"
                      + (" + persistence of yesterday's variance." if kind == "garch" else "."),
                      [("ω", "baseline variance"),
                       ("α", f"reaction to a fresh shock (= {m.get('alpha')})"),
                       ("β", f"persistence of past variance (= {m.get('beta')})" if kind == "garch"
                        else "—"),
                       ("ε²", "yesterday's squared return")],
                      f"α+β = {m.get('persistence')} — "
                      + ("shocks linger for a long time" if (m.get('persistence') or 0) > 0.9
                         else "volatility mean-reverts fairly quickly"))])],
            kicker="Conditional variance, riding the shocks"))
        chapters.append(_note(
            "persistence", "Reading α, β and persistence", "What the numbers mean",
            f"α = {m.get('alpha')} is how hard a new shock hits tomorrow's variance; β = "
            f"{m.get('beta')} is how much old variance carries forward. Their sum, "
            f"{m.get('persistence')}, is PERSISTENCE — how slowly calm returns after a storm. "
            "Close to 1 means shocks echo for weeks (the norm in real markets)."))
    chapters.append(_note(
        "caveats", "Two things GARCH won't do", "Asymmetry & fat tails",
        "Plain GARCH is symmetric — a crash and a rally of equal size raise volatility equally, "
        "but real markets show a LEVERAGE effect (crashes hit harder); EGARCH/GJR fix that. And "
        "Gaussian errors understate tail risk — practitioners use a Student-t. Know these before "
        "you quote a Value-at-Risk."))

    tail = [testing_chapter(trace)] if trace.test_rows else []
    if trace.param_spec:
        tail.append(hyperparams_chapter(trace, facts))
    tail.append(verdict_chapter(facts, guide, name))
    quiz = quiz_chapter(facts, name)
    if quiz:
        tail.append(quiz)
    full = [*chapters, *tail]
    return [roadmap_chapter(f"{name}: forecasting risk itself",
                            full, str(guide.get("one_liner", ""))), *full]


# ---- econometrics (OLS · logit · probit · poisson · quantile · negative binomial) ------------


@register_lesson("econometrics")
def econometrics_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["linear"])
    inf = ((trace.series or {}).get("inference") or {})
    rows = [r for r in inf.get("rows", []) if r.get("feature") != "intercept"]
    kind = str(inf.get("kind", "ols"))
    stat = str(inf.get("stat_name", "t"))
    lead = max(rows, key=lambda r: abs(r.get("stat", 0)), default=None)
    name = facts.display_name if facts else "this model"

    chapters: list[Chapter] = [data_chapter(trace)]
    chapters.append(_note(
        "mechanics", "The mechanics in one minute", "Same recipe as linear/logistic",
        "Under the hood this is the weighted-sum recipe: every variable gets a coefficient, "
        "they sum into a score"
        + (", and a link function turns the score into a probability (sigmoid for logit, the "
           "normal CDF for probit)." if trace.task == "classification"
           else (" — and for counts, e raised to that score gives the RATE." if kind == "poisson"
                 else " — and that score is the prediction."))
        + " But econometrics asks a harder question than prediction: can we TRUST each "
        "coefficient, or could it be noise?"))
    if kind == "ols" and (trace.series or {}).get("regression_fit"):
        chapters.append(chapter(
            "least-squares", "The best-fit line",
            [step("residuals",
                  "First, the fit itself. The line sweeps into your data; each point's residual is "
                  "the vertical segment to its predicted point on the line, and OLS minimises the "
                  "total of those gaps SQUARED. Only once we have this line do we ask whether its "
                  "slope can be trusted.",
                  duration_ms=DUR_SHOW, anim=AnimDirective(kind="regression-fit"),
                  math=[_m("Least squares", "min Σ (yᵢ − ŷᵢ)²",
                           "Make the squared residuals as small as possible.",
                           [("yᵢ", "the actual point"), ("ŷᵢ", "the predicted point on the line")],
                           "")])],
            kicker="Least squares, made visible"))
    chapters.append(_note(
        "sampling-story", "The sampling story", "Why coefficients wobble",
        "Imagine re-running history: a different sample of people/firms/months would give a "
        "slightly different coefficient every time. Those hypothetical re-runs form a bell "
        "curve around the truth; the STANDARD ERROR is that bell's width. Everything on the "
        "inference table — t, p, confidence interval — is read off this one picture.",
        math=[_m(f"The {stat}-statistic", f"{stat} = coef / SE",
                 "How many bell-widths the estimate sits away from zero.",
                 [("coef", "the fitted coefficient"),
                  ("SE", "the standard error — the wobble of the estimate")],
                 (f"{lead['feature']}: {lead['coef']} / {lead['se']} = {lead['stat']}"
                  if lead else ""))]))
    if rows:
        chapters.append(chapter(
            "inference-table", "The inference table",
            [step(
                "inference",
                f"Here is the real fit on your data ({inf.get('n')} rows, "
                f"{inf.get('fit', {}).get('name')} = {inf.get('fit', {}).get('value')}). Each "
                f"coefficient arrives with its SE, {stat}-statistic, p-value and 95% "
                "confidence interval. Watch the CI whiskers: an interval that CROSSES ZERO "
                "glows red — with this data you cannot rule out 'no effect at all'.",
                duration_ms=DUR_SHOW,
                anim=AnimDirective(kind="inference-table", substeps=max(1, len(rows))),
                math=[_m("The p-value, honestly", "p = P(data this extreme | true effect = 0)",
                         "If the truth were zero, how surprising is what we observed?",
                         [("p < 0.05", "conventional 'statistically significant' line"),
                          ("caution", "significance is about EVIDENCE, not size or importance")],
                         (f"{lead['feature']}: p = {lead['p']}" if lead else ""))],
            )],
            kicker="SE · t · p · confidence intervals, on your fit"))
    if kind == "logit" and lead and lead.get("exp_coef") is not None:
        chapters.append(_note(
            "odds-ratios", "Reading logit: odds ratios", "e^β — the exam favourite",
            f"Logit coefficients live on the log-odds scale, so exponentiate to speak human: "
            f"e^({lead['coef']}) = {lead['exp_coef']} — one more unit of {lead['feature']} "
            f"multiplies the ODDS by {lead['exp_coef']}. That is a change in odds, NOT in "
            "probability: for probabilities, compute marginal effects at a meaningful point "
            "(≈ β·p·(1−p)).",
            math=[_m("Odds ratio", "OR = e^β",
                     "How the odds multiply per one-unit increase.",
                     [("β", "the logit coefficient"), ("OR", "odds ratio")],
                     f"{lead['feature']}: e^{lead['coef']} = {lead['exp_coef']}")]))
    elif kind == "probit":
        chapters.append(_note(
            "latent-story", "Reading probit: the hidden score", "A threshold crossing",
            "Probit's story: each observation has a hidden continuous score y* = Xβ + noise, "
            "with standard-normal noise. We only see y = 1 when the score crosses zero, so "
            "P(y=1) = Φ(Xβ). No odds-ratio shortcut exists here — interpret through marginal "
            "effects. In practice logit and probit trace nearly identical S-curves."))
    elif kind == "poisson" and lead and lead.get("exp_coef") is not None:
        chapters.append(_note(
            "rate-ratios", "Reading poisson: rate ratios", "Counts multiply, never go negative",
            f"The model sets the expected COUNT to e^(Xβ) — always positive, as counts must "
            f"be. Exponentiated coefficients are rate ratios: e^({lead['coef']}) = "
            f"{lead['exp_coef']} means one more unit of {lead['feature']} multiplies the "
            f"expected count by {lead['exp_coef']}. Check overdispersion: if the variance "
            "clearly exceeds the mean, standard errors are too small — reach for negative "
            "binomial."))
    elif kind == "ols":
        chapters.append(_note(
            "assumptions", "The assumptions doing the work", "Gauss–Markov, in plain words",
            "OLS is only 'best' under conditions: the relationship is linear; the errors "
            "average zero given the X's (no omitted confounders!); constant error variance "
            "(else use robust SEs); no perfect collinearity. Break the exogeneity one and the "
            "coefficient stops being causal — the classic omitted-variable-bias exam trap."))
    return _finish(f"{name}: estimation AND inference", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


# ---- bagged ensembles (random forest · extra trees · bagging) --------------------------------


@register_lesson("random_forest")
def random_forest_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["trees"])
    key = facts.key if facts else "random_forest"
    name = facts.display_name if facts else "Random Forest"

    chapters = [
        data_chapter(trace),
        chapter("one-tree", "Why one tree isn't enough",
                [step("one-tree",
                      "A single deep tree memorises: wiggle the data slightly and the whole "
                      "tree can flip — high VARIANCE. Watch one of the ensemble's trees grow "
                      "on your data; it's good on average but jumpy between samples. The fix "
                      "isn't a better tree. It's a crowd of different ones.",
                      duration_ms=DUR_SHOW,
                      anim=AnimDirective(kind="tree-grow", substeps=max(1, _count_tree(trace.tree))))],
                kicker="High variance — the disease bagging cures"),
        _widget("bootstrap", "Every tree gets its own bag", "Bootstrap sampling",
                "Each tree trains on a BOOTSTRAP sample: rows drawn with replacement until the "
                "bag is as big as the data. Some rows appear twice, about a third don't appear "
                "at all — those out-of-bag rows become a free honest test set. Different bags "
                "→ different trees → different mistakes.", "bootstrap-hat"),
    ]
    if key == "random_forest":
        chapters.append(_note(
            "feature-menu", "…and its own feature menu", "The 'random' in random forest",
            "Bags alone aren't enough: strong features would still dominate every tree and the "
            "crowd would agree too much. So at EVERY split, the forest shows the tree only a "
            "random menu of features (typically √p of them). Forced variety = decorrelated "
            "mistakes = a vote worth taking."))
    elif key == "extra_trees":
        chapters.append(_note(
            "random-cuts", "Extra Trees: don't even search", "Randomness squared",
            "Extra Trees goes one step wilder: instead of auditioning every threshold, each "
            "split THROWS A DART — a random cut-point per candidate feature, still scored, "
            "best dart kept. Cheaper per split and even more decorrelated trees; a few more "
            "of them buys the accuracy back."))
    else:  # bagging
        chapters.append(_note(
            "plain-bagging", "Bagging: the general recipe", "Any model, many bags",
            "Bagging is the general trick: train the SAME model on many bootstrap bags and "
            "average. It only calms variance — a biased base model stays biased. A random "
            "forest is exactly bagged trees PLUS the random feature menus."))
    chapters.append(_widget(
        "vote", "The crowd votes", "Averaging kills variance",
        "To predict, every tree votes (classification) or every prediction is averaged "
        "(regression). Individual trees are jumpy; their average is calm — that's the whole "
        "theorem. One noisy tree can't flip the verdict.", "vote-box",
        math=[_m("Why averaging works", "Var(mean of B trees) ≈ ρσ² + (1−ρ)σ²/B",
                 "More trees shrink the second term; DECORRELATION (small ρ) shrinks the first.",
                 [("σ²", "one tree's variance"), ("B", "number of trees"),
                  ("ρ", "correlation between trees — what bags + menus attack")],
                 "")]))
    return _finish(f"{name}, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


@register_lesson("adaboost")
def adaboost_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["trees"])
    chapters = [
        data_chapter(trace),
        chapter("stump", "The weakest learner there is",
                [step("stump",
                      "AdaBoost's building block is a STUMP — one question, two answers. "
                      "Alone it's barely better than a coin flip. Watch one grow on your data.",
                      duration_ms=DUR_SCENE,
                      anim=AnimDirective(kind="tree-grow", ref={"max_depth": 1}, substeps=3))],
                kicker="One question, two answers"),
        _widget("reweight", "Inflate the mistakes", "AdaBoost's own move",
                "Every row starts with equal weight. After each stump, the rows it got WRONG "
                "have their weights inflated — the next stump is forced to face them. That's "
                "the difference from gradient boosting: AdaBoost reweights ROWS, gradient "
                "boosting refits RESIDUALS.", "weight-grow",
                math=[_m("A stump's say", "α = ½·ln((1−ε)/ε)",
                         "The lower a stump's weighted error, the louder its vote.",
                         [("ε", "the stump's weighted error rate"),
                          ("α", "its voting weight in the final ensemble")],
                         "ε = 0.5 (coin flip) → α = 0: no say · ε = 0.1 → α ≈ 1.1: a loud vote")]),
        _note("outliers", "The Achilles heel", "Why outliers hurt",
              "A mislabelled row gets inflated round after round until the ensemble obsesses "
              "over it — AdaBoost is famously outlier-sensitive. Check the weight distribution "
              "when it underperforms; if a handful of rows dominate, clean them or switch to "
              "gradient boosting."),
    ]
    return _finish("AdaBoost, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


@register_lesson("gaussian_process")
def gaussian_process_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["trees"])
    chapters = [
        data_chapter(trace),
        _note("functions", "A distribution over FUNCTIONS", "The big idea",
              "Every model so far learned one function. A gaussian process holds a whole CLOUD "
              "of plausible functions and lets the data thin it out. The prediction at any "
              "point is the cloud's mean there — and the cloud's spread is an honest error "
              "bar, for free."),
        _widget("pinning", "Data pins the cloud down", "Prior → posterior",
                "Before data, the cloud is wide everywhere (the prior). Each observation PINS "
                "the functions: they must pass nearby. Watch the band collapse at the points "
                "and flare between them — the model literally telling you where it doesn't "
                "know.", "gp-band",
                math=[_m("The kernel — similarity is the assumption",
                         "k(x, x′) = exp(−‖x − x′‖²/(2ℓ²))",
                         "Nearby inputs must have similar outputs; ℓ says what 'nearby' means.",
                         [("k", "covariance between two points' function values"),
                          ("ℓ", "the length-scale — small ℓ = wiggly, large ℓ = smooth")],
                         "")]),
        _note("cost", "The price of honesty", "Why GPs stay small",
              "Exact GP inference inverts an n×n matrix — O(n³). A few thousand rows is the "
              "practical ceiling, which is why GPs shine on small precious data (experiments, "
              "simulator surrogates, Bayesian optimisation) and hand the big-data jobs to "
              "forests and networks. Note: the staged training view here uses a tree stand-in "
              "until the dedicated GP tracer lands — the mechanism above is the real story."),
    ]
    return _finish("Gaussian processes, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


# ---- svm & naive bayes ------------------------------------------------------------------------


@register_lesson("svm")
def svm_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["svm", "linear"])
    chapters = [
        data_chapter(trace),
        _widget("margin", "The widest street wins", "SVM's own move",
                "Many lines separate the classes; the SVM picks the one with the WIDEST street "
                "— the maximum margin. Only the points touching the street (the support "
                "vectors) define it: delete every other point and the boundary doesn't move an "
                "inch. C prices violations: big C = a strict narrow street, small C = a "
                "tolerant wide one.", "margin-street",
                math=[_m("Hinge loss", "loss = max(0, 1 − y·f(x))",
                         "Zero for points comfortably on their side; grows for street-crashers.",
                         [("y", "the true class, coded ±1"),
                          ("f(x)", "signed distance from the boundary"),
                          ("1", "the margin's edge — inside it you pay")],
                         "")]),
        _widget("kernel", "The kernel trick", "Bending the street",
                "When no straight street exists, LIFT the points into a higher-dimensional "
                "space where one does — without ever computing the new coordinates. The kernel "
                "supplies the dot products directly; a flat cut up there lands back down as a "
                "curved boundary. RBF's γ sets how tightly the lift wraps each point.",
                "kernel-lift"),
        _train("fit", "The fitted view", "On your data",
               "The staged view shows the fitted stand-in's weight-based picture — the linear "
               "skeleton of the SVM story. Scale your features before trusting any SVM: the "
               "street is measured with a ruler, and unscaled features bend the ruler."),
    ]
    return _finish("Support vector machines, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


@register_lesson("naive_bayes")
def naive_bayes_lesson(trace: ModelTrace, facts: ModelFacts | None) -> list[Chapter]:
    guide = explainer_for_chain(["linear"])
    chapters = [
        data_chapter(trace),
        _note("bayes-rule", "Bayes' rule, in plain words", "Flip the question",
              "We want P(class | features) but data gives us the reverse — how features look "
              "WITHIN each class. Bayes' rule flips it: start from the prior (how common the "
              "class is), multiply by how well the row's features fit that class, and compare "
              "across classes.",
              math=[_m("Bayes' rule", "P(class|x) ∝ P(class) · P(x|class)",
                       "Prior belief times likelihood of the evidence.",
                       [("P(class)", "the prior — the class's share of the data"),
                        ("P(x|class)", "how typical this row's values are for that class")],
                       "")]),
        _widget("race", "The likelihood race", "Naive Bayes' own move",
                "For one row, each class multiplies in its likelihood for every feature, one "
                "at a time — a race of shrinking products (done in log-space in practice). The "
                "taller product wins. The 'NAIVE' part: features are treated as independent "
                "within a class — usually false, but the winner of the race is often still "
                "right, which is all classification needs.", "bayes-race"),
        _note("when", "Why it survives being wrong", "Miscalibrated but useful",
              "Because independence is violated, the probabilities are over-confident — don't "
              "read them as calibrated. But the ARGMAX is robust, training is one pass of "
              "counting, and it works on data too small for anything else. That's why spam "
              "filters shipped it for decades."),
    ]
    return _finish("Naive Bayes, from zero", str(guide.get("one_liner", "")),
                   chapters, trace, facts, guide)


def _count_tree(node: dict | None) -> int:
    if not node:
        return 0
    return 1 + _count_tree(node.get("left")) + _count_tree(node.get("right"))
