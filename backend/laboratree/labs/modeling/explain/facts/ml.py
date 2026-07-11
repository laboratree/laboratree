"""Curated facts for the classic-ML models (17)."""

from __future__ import annotations

from . import Alternative, HyperparameterDoc, ModelFacts, register_facts


def _alt(model: str, when: str) -> Alternative:
    return Alternative(model=model, prefer_when=when)


def _hp(name: str, plain: str, effect: str, rng: str = "") -> HyperparameterDoc:
    return HyperparameterDoc(name=name, plain=plain, effect=effect, typical_range=rng)


register_facts(ModelFacts(
    key="xgboost", display_name="XGBoost", family="xgboost",
    one_liner="Boosted trees with exact gradient math — the tabular-data champion.",
    pros=["Usually the strongest baseline on tabular data with modest tuning",
          "Handles non-linearities and feature interactions automatically",
          "Built-in regularisation (λ, γ) and missing-value handling",
          "Fast, parallel, battle-tested implementation"],
    cons=["Easy to overfit small/noisy data if depth or rounds run wild",
          "Not readable as one rule — needs SHAP/importances to explain"],
    limitations=["Extrapolates poorly outside the training range",
                 "Needs enough rows per leaf to estimate good values"],
    use_when=["Structured rows-and-columns data where accuracy matters most.",
              "Mixed feature scales/types with likely interactions."],
    alternatives=[
        _alt("Random forest", "you want strong results with almost zero tuning"),
        _alt("Logistic regression", "you need coefficients you can defend in a report"),
        _alt("Neural network", "the data is huge and unstructured (images, text, audio)"),
    ],
    hyperparameters=[
        _hp("eta", "Learning rate — how much of each tree's correction is applied.",
            "Lower = steadier but needs more rounds; higher = fast but can overshoot.", "0.01–0.3"),
        _hp("max_depth", "Question-levels per tree.",
            "Deeper trees capture interactions but memorise noise.", "3–8"),
        _hp("n_estimators", "How many trees are stacked.",
            "More rounds = more capacity; pair large values with small eta.", "100–1000"),
        _hp("reg_lambda", "L2 penalty on leaf values (the λ in the similarity score).",
            "Bigger λ shrinks similarity scores and leaf outputs — more cautious trees.", "0–10"),
        _hp("gamma", "Minimum gain a split must earn (the toll).",
            "Raise it to prune marginal splits and simplify trees.", "0–5"),
        _hp("min_child_weight", "Minimum Σh (evidence) each side of a split needs.",
            "Raise it to stop splits backed by too few/too-confident rows.", "1–10"),
        _hp("subsample", "Fraction of rows each tree sees.",
            "Below 1.0 adds randomness that fights overfitting.", "0.6–1.0"),
        _hp("colsample_bytree", "Fraction of features each tree may use.",
            "Below 1.0 decorrelates the trees, like a random forest.", "0.6–1.0"),
    ],
))

register_facts(ModelFacts(
    key="gradient_boosting", display_name="Gradient Boosting", family="trees",
    one_liner="Trees added one by one, each fixing the last one's mistakes.",
    pros=["Excellent accuracy on tabular data", "Flexible: any differentiable loss",
          "Shallow trees keep each stage interpretable"],
    cons=["Sequential — slower to train than a forest", "Sensitive to noisy labels (it chases every residual)"],
    limitations=["Same extrapolation limits as all trees"],
    use_when=["You want boosting's accuracy with scikit-learn simplicity."],
    alternatives=[
        _alt("XGBoost", "you want regularised boosting (λ, γ) and raw speed"),
        _alt("Random forest", "labels are noisy — averaging beats chasing residuals"),
    ],
    hyperparameters=[
        _hp("learning_rate", "How much each tree's correction counts.",
            "Lower needs more trees but generalises better.", "0.01–0.3"),
        _hp("max_iter", "Number of boosting rounds.", "More rounds = more capacity.", "100–500"),
        _hp("max_depth", "Depth of each tree.", "Keep shallow (2–6); depth is the overfit dial.", "2–6"),
    ],
))

register_facts(ModelFacts(
    key="decision_tree", display_name="Decision Tree", family="trees",
    one_liner="A chain of yes/no questions you can read like a flowchart.",
    pros=["Fully interpretable — you can read the rules", "No scaling needed; handles mixed features",
          "Fast to train and predict"],
    cons=["High variance: a small data change can flip the whole tree",
          "Greedy splits can miss better global structures"],
    limitations=["One tree rarely wins on accuracy — it's the building block, not the building"],
    use_when=["You must explain every decision (compliance, medicine).",
              "As the weak learner inside forests and boosting."],
    alternatives=[
        _alt("Random forest", "you can trade readability for much better accuracy"),
        _alt("XGBoost", "accuracy is the goal and a single tree clearly underfits"),
    ],
    hyperparameters=[
        _hp("max_depth", "How many question-levels the tree may grow.",
            "The main overfit dial: deep = memorise, shallow = generalise.", "3–10"),
        _hp("n_estimators", "(boosting view) trees stacked when shown as an ensemble.",
            "More trees = more corrections.", "1–6"),
        _hp("learning_rate", "(boosting view) trust per tree.",
            "Lower = smaller, safer corrections.", "0.1–1.0"),
    ],
))

register_facts(ModelFacts(
    key="random_forest", display_name="Random Forest", family="trees",
    one_liner="Many decorrelated trees vote — strong with almost no tuning.",
    pros=["Great accuracy out of the box", "Robust to noise and outliers (averaging)",
          "Parallel training; useful feature importances; OOB error for free"],
    cons=["Bigger and slower to predict than one tree", "Less accurate than tuned boosting on most benchmarks"],
    limitations=["Cannot extrapolate beyond the training range"],
    use_when=["You need a dependable strong baseline today, not after a tuning campaign."],
    alternatives=[
        _alt("XGBoost", "you have tuning budget and want the extra accuracy"),
        _alt("Decision tree", "you must read the model as explicit rules"),
    ],
    hyperparameters=[
        _hp("n_estimators", "Number of trees in the forest.",
            "More trees = smoother vote, slower predict; returns flatten out.", "100–500"),
        _hp("max_depth", "Depth cap per tree.", "Often left unlimited; cap to shrink memory/overfit.", "none–20"),
        _hp("max_features", "Features each split may consider.",
            "Smaller = more decorrelated trees (the 'random' in the name).", "sqrt(p)"),
    ],
))

register_facts(ModelFacts(
    key="extra_trees", display_name="Extra Trees", family="trees",
    one_liner="A forest with random cut-points — extra randomness, lower variance.",
    pros=["Even faster to train than a forest (no threshold search)", "Extra randomness fights overfitting"],
    cons=["Slightly worse per-tree quality; needs a few more trees"],
    limitations=["Same tree-family extrapolation limits"],
    use_when=["Random forest overfits or takes too long — same API, more randomness."],
    alternatives=[_alt("Random forest", "you want the classic bias/variance point"),
                  _alt("XGBoost", "you want accuracy over speed")],
    hyperparameters=[
        _hp("n_estimators", "Number of trees.", "More = smoother; returns flatten.", "100–500"),
        _hp("max_depth", "Depth cap per tree.", "Cap to regularise.", "none–20"),
    ],
))

register_facts(ModelFacts(
    key="adaboost", display_name="AdaBoost", family="trees",
    one_liner="Reweights the rows it got wrong so the next stump must face them.",
    pros=["Simple, classical boosting with few knobs", "Stumps keep every stage readable"],
    cons=["Very sensitive to outliers — wrong rows get ever-bigger weights",
          "Usually beaten by gradient boosting on accuracy"],
    limitations=["Best with clean labels and weak base learners"],
    use_when=["A teaching-clean boosting baseline, or very clean small datasets."],
    alternatives=[
        _alt("Gradient boosting", "labels are noisy — fitting residuals beats inflating weights"),
        _alt("XGBoost", "you want modern regularised boosting"),
    ],
    hyperparameters=[
        _hp("n_estimators", "Number of weighted stumps.", "More stumps = more capacity.", "50–500"),
        _hp("learning_rate", "Shrinks each stump's say (α).", "Lower = slower, steadier.", "0.1–1.0"),
    ],
))

register_facts(ModelFacts(
    key="bagging", display_name="Bagging", family="trees",
    one_liner="Train on bootstrap samples and average — variance melts away.",
    pros=["Turns any unstable model into a stable one", "Trivially parallel"],
    cons=["Doesn't help low-variance models", "Loses single-model interpretability"],
    limitations=["Reduces variance, not bias — a bad base model stays bad"],
    use_when=["Your base model is good on average but jumpy between samples."],
    alternatives=[_alt("Random forest", "bagging trees? The forest adds feature-sampling for free"),
                  _alt("XGBoost", "the base model UNDERfits — boosting reduces bias")],
    hyperparameters=[
        _hp("n_estimators", "Number of bootstrap models averaged.", "More = smoother predictions.", "10–100"),
    ],
))

register_facts(ModelFacts(
    key="logistic_regression", display_name="Logistic Regression", family="linear",
    one_liner="Weighted sum squeezed through a sigmoid into a probability.",
    pros=["Coefficients are directly interpretable (odds ratios)",
          "Well-calibrated probabilities; fast; a rock-solid baseline",
          "Convex loss — one global optimum, reproducible fits"],
    cons=["Only linear decision boundaries (unless you engineer features)",
          "Needs feature scaling for stable optimisation"],
    limitations=["Struggles when classes are perfectly separable (weights blow up — regularise)"],
    use_when=["You need probabilities you can explain, fast.",
              "As the honest baseline every fancier model must beat."],
    alternatives=[
        _alt("XGBoost", "interactions/non-linearities matter more than interpretability"),
        _alt("Logit (econometrics)", "you need inference: p-values and confidence intervals"),
    ],
    hyperparameters=[
        _hp("C", "Inverse regularisation strength.", "Smaller C = stronger shrinkage of weights.", "0.01–100"),
        _hp("max_iter", "Optimiser iteration cap.", "Raise if the solver warns about convergence.", "100–1000"),
    ],
))

register_facts(ModelFacts(
    key="linear_regression", display_name="Linear Regression", family="linear",
    one_liner="The best-fit line: every feature gets a per-unit effect.",
    pros=["Instant to fit, trivial to explain", "Coefficients = per-unit effects",
          "The foundation every other regressor is compared against"],
    cons=["Assumes linearity and additive effects", "Sensitive to outliers (squared loss)"],
    limitations=["Collinear features make coefficients unstable"],
    use_when=["Roughly linear relationships, or as the first honest baseline."],
    alternatives=[
        _alt("Ridge/Lasso", "many or correlated features — regularise"),
        _alt("XGBoost", "the relationship is clearly non-linear"),
        _alt("OLS (econometrics)", "you need standard errors and confidence intervals"),
    ],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="ridge", display_name="Ridge (L2)", family="linear",
    one_liner="Linear regression where big weights cost you — shrinks, never zeroes.",
    pros=["Tames collinearity and overfitting", "Keeps all features (smooth shrinkage)", "Closed-form fast"],
    cons=["Doesn't do feature selection", "Coefficients biased toward zero"],
    limitations=["Still a linear model"],
    use_when=["More features than you'd like, correlated predictors, small n."],
    alternatives=[_alt("Lasso", "you want irrelevant features zeroed out entirely"),
                  _alt("Elastic Net", "correlated groups where lasso picks arbitrarily")],
    hyperparameters=[
        _hp("alpha", "Strength of the L2 penalty (λ).",
            "Bigger = smaller weights, more bias, less variance.", "0.01–100"),
    ],
))

register_facts(ModelFacts(
    key="lasso", display_name="Lasso (L1)", family="linear",
    one_liner="Shrinks weights all the way to zero — feature selection for free.",
    pros=["Automatic feature selection (sparse models)", "Great when only a few features matter"],
    cons=["Among correlated features it keeps one arbitrarily", "Can underfit if alpha is too big"],
    limitations=["Selects at most n features when p > n"],
    use_when=["You suspect most features are noise and want the model to say which aren't."],
    alternatives=[_alt("Ridge", "all features plausibly matter a little"),
                  _alt("Elastic Net", "correlated feature groups should enter together")],
    hyperparameters=[
        _hp("alpha", "Strength of the L1 penalty.", "Bigger = more coefficients exactly zero.", "0.001–10"),
    ],
))

register_facts(ModelFacts(
    key="elastic_net", display_name="Elastic Net", family="linear",
    one_liner="The dial between ridge and lasso for correlated features.",
    pros=["Sparse like lasso but keeps correlated groups together", "Two dials cover the whole L1/L2 spectrum"],
    cons=["Two hyperparameters to tune instead of one"],
    limitations=["Still linear"],
    use_when=["High-dimensional data with correlated blocks (genomics, text n-grams)."],
    alternatives=[_alt("Lasso", "features are mostly independent"),
                  _alt("Ridge", "you don't want any zeroed out")],
    hyperparameters=[
        _hp("alpha", "Overall penalty strength.", "Bigger = more total shrinkage.", "0.001–10"),
        _hp("l1_ratio", "The blend dial: 0 = pure ridge, 1 = pure lasso.",
            "Slide toward 1 for sparsity, toward 0 for group-keeping.", "0.1–0.9"),
    ],
))

register_facts(ModelFacts(
    key="knn", display_name="K-Nearest Neighbors", family="knn",
    one_liner="Memorize everything; predict from the most similar rows.",
    pros=["No training at all — the data IS the model", "Naturally non-linear decision boundaries",
          "One intuitive knob (k)"],
    cons=["Slow at prediction time (searches all rows)", "Needs feature scaling — one big-unit column hogs the ruler"],
    limitations=["Curse of dimensionality: in many dimensions everything is 'far'",
                 "Struggles with imbalanced classes (majority swamps the vote)"],
    use_when=["Small-to-medium data with a meaningful distance; quick non-linear baseline."],
    alternatives=[_alt("Random forest", "many features or big data — distance stops meaning much"),
                  _alt("Logistic regression", "you need speed at prediction time")],
    hyperparameters=[
        _hp("n_neighbors", "How many neighbours vote (k).",
            "Small k = jagged, flexible boundary; large k = smooth, stable.", "3–25 (odd)"),
    ],
))

register_facts(ModelFacts(
    key="svm", display_name="Support Vector Machine", family="linear",
    one_liner="Finds the widest street between the classes; kernels bend it.",
    pros=["Maximum-margin boundaries generalise well", "Kernel trick captures non-linearity without exploding features",
          "Only the support vectors matter — sparse solution"],
    cons=["Scales badly past ~10⁴ rows (quadratic-ish training)",
          "Probabilities need extra calibration; kernels need scaling + tuning"],
    limitations=["Kernel choice is make-or-break; hard to interpret in kernel space"],
    use_when=["Medium-sized, scaled data with complex boundaries (text, bio-signals)."],
    alternatives=[_alt("Logistic regression", "the boundary is roughly linear anyway"),
                  _alt("XGBoost", "large tabular data — trees scale and skip scaling")],
    hyperparameters=[
        _hp("C", "Margin hardness: how expensive violations are.",
            "Big C = narrow, strict street (overfit risk); small C = wide, tolerant street.", "0.1–100"),
    ],
))

register_facts(ModelFacts(
    key="naive_bayes", display_name="Naive Bayes", family="linear",
    one_liner="Bayes' rule with a bold independence shortcut — tiny-data friendly.",
    pros=["Trains on almost no data", "Extremely fast; naturally multiclass",
          "Great for text/count features"],
    cons=["The independence assumption is usually false (probabilities over-confident)"],
    limitations=["Correlated features double-count evidence"],
    use_when=["Text classification, tiny datasets, or a millisecond-budget baseline."],
    alternatives=[_alt("Logistic regression", "you have enough data to learn real weights"),
                  _alt("XGBoost", "accuracy matters and features interact")],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="mlp", display_name="Neural Network (MLP)", family="nn",
    one_liner="Layers of weighted sums learn by sending blame backwards.",
    pros=["Universal approximator — any shape of relationship",
          "Scales to huge data; foundations of all deep learning"],
    cons=["Data-hungry; unstable on small tables", "A black box without extra tooling",
          "Sensitive to scaling, initialisation, learning rate"],
    limitations=["On modest tabular data, boosted trees usually win"],
    use_when=["Lots of rows and smooth non-linear structure, or as a stepping stone to deep models."],
    alternatives=[_alt("XGBoost", "tabular data of ordinary size — trees usually win"),
                  _alt("Logistic regression", "you need interpretability, not curves")],
    hyperparameters=[
        _hp("hidden", "Neurons in the hidden layer.", "More = more capacity and more overfit risk.", "8–128"),
        _hp("max_iter", "Training epochs.", "More epochs = lower train loss; watch the val curve.", "100–1000"),
    ],
))

register_facts(ModelFacts(
    key="gaussian_process", display_name="Gaussian Process", family="trees",
    one_liner="A distribution over functions — predictions with honest uncertainty.",
    pros=["Uncertainty bands for every prediction, for free",
          "Excellent on small, smooth datasets", "Kernel encodes your assumptions explicitly"],
    cons=["O(n³) training — dies past a few thousand rows", "Kernel choice needs expertise"],
    limitations=["High dimensions weaken 'nearby means similar'"],
    use_when=["Small precious data where knowing the error bars matters (experiments, surrogate models)."],
    alternatives=[_alt("Random forest", "more rows than a GP can chew"),
                  _alt("Linear regression", "the trend is simple — skip the machinery")],
    hyperparameters=[],
))
