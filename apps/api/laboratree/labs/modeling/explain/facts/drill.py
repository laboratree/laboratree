"""Drill content for every model: real-world applications, edge cases, and exam Q&A.

Kept in one file so the exam-prep layer can be reviewed (and extended) in one place. Applied
onto the registered ModelFacts by ``enrich()`` at load time. Each quiz ALSO self-generates
questions from the facts (alternatives/weaknesses/knobs), so these are the hand-written extras
a professor would actually ask.
"""

from __future__ import annotations

from . import FACTS, ExamQA

APPLICATIONS: dict[str, list[str]] = {
    "xgboost": [
        "Credit scoring and loan-default prediction at banks (tabular borrower features).",
        "Kaggle-style demand forecasting, churn, fraud and insurance-claim triage.",
    ],
    "gradient_boosting": [
        "Insurance pricing and risk models where each stage must be auditable.",
        "Marketing-response and uplift models on customer tables.",
    ],
    "decision_tree": [
        "Medical triage flowcharts and credit 'knock-out' rules a regulator can read.",
        "Segmenting survey respondents into explainable groups.",
    ],
    "random_forest": [
        "Credit risk and churn baselines shipped without a tuning campaign.",
        "Remote sensing / land-cover classification; gene-expression classification.",
    ],
    "extra_trees": [
        "Same jobs as random forest when training speed matters (large feature sets).",
        "Sensor-data classification with noisy measurements.",
    ],
    "adaboost": [
        "Face detection (the original Viola–Jones detector is AdaBoost on stumps).",
        "Small clean tabular problems needing a simple boosted baseline.",
    ],
    "bagging": [
        "Stabilising any jumpy model — e.g. bagged trees for demand estimates.",
        "Reducing variance of regression models on small samples.",
    ],
    "logistic_regression": [
        "Loan approval / default probability — the regulator-friendly industry default.",
        "Clinical risk scores (e.g. probability of readmission) and A/B conversion models.",
    ],
    "linear_regression": [
        "Hedonic pricing: how bedrooms, location and size move house prices.",
        "Wage equations in labour economics (returns to education/experience).",
    ],
    "ridge": [
        "Macro forecasting with many correlated indicators.",
        "Any regression where p is large relative to n (marketing mix models).",
    ],
    "lasso": [
        "Variable selection in high-dimensional econometrics (post-lasso inference).",
        "Genomics / text models where only a few of thousands of features matter.",
    ],
    "elastic_net": [
        "Genomic prediction with correlated gene blocks.",
        "Text regression on n-gram features (correlated groups).",
    ],
    "knn": [
        "Recommenders' 'users like you' step; product similarity lookups.",
        "Imputing missing values from the most similar complete rows.",
    ],
    "svm": [
        "Text classification (spam, sentiment) on TF-IDF features.",
        "Bioinformatics: protein/gene classification on medium-sized data.",
    ],
    "naive_bayes": [
        "Spam filtering — the classic production example.",
        "Real-time document/ticket routing where milliseconds matter.",
    ],
    "mlp": [
        "Tabular problems with big data and smooth non-linearities (energy load).",
        "The building block: every deep model is MLP layers plus structure.",
    ],
    "gaussian_process": [
        "Bayesian optimisation (tuning other models' hyperparameters!).",
        "Emulating expensive simulations/experiments with uncertainty bands.",
    ],
    "cnn": [
        "Defect detection on production lines; medical imaging.",
        "Audio/spectrogram classification; satellite imagery for crop yields (ag-econ).",
    ],
    "rnn": [
        "Short-horizon demand/sales forecasting from recent history.",
        "Sensor-stream monitoring (predictive maintenance) and text snippets.",
    ],
    "transformer": [
        "Language models (GPT/BERT), translation, code assistants.",
        "Long-horizon multivariate forecasting and recommendation at scale.",
    ],
    "kmeans": [
        "Customer segmentation for pricing and campaign design.",
        "Image color quantisation; sensor grouping; store clustering.",
    ],
    "dbscan": [
        "Geo-spatial clustering (crime/complaint hot-spots, ride-hailing zones).",
        "Fraud rings: dense pockets of related transactions with noise ignored.",
    ],
    "gmm": [
        "Market segments with soft membership ('60% price-sensitive').",
        "Speaker identification and background subtraction in vision.",
    ],
    "hierarchical": [
        "Taxonomies: product catalogs, gene-expression heatmaps with dendrograms.",
        "Survey/behavioural segmentation where the tree itself is the deliverable.",
    ],
    "spectral": [
        "Community detection in social/transaction graphs.",
        "Image segmentation; grouping correlated assets.",
    ],
    "isolation_forest": [
        "Transaction fraud screening at scale.",
        "IT/IoT telemetry anomaly detection (server metrics, sensor faults).",
    ],
    "lof": [
        "Local card-fraud patterns (odd for THIS customer's neighbourhood).",
        "Quality control where densities differ across product lines.",
    ],
    "one_class_svm": [
        "Machine-health monitoring trained only on healthy-state data.",
        "Intrusion detection from clean baseline traffic.",
    ],
    "ets": [
        "Retail demand and call-volume forecasting (the M-competition workhorse).",
        "Inventory planning with trend + weekly/yearly seasonality.",
    ],
    "sarima": [
        "Monthly macro series (CPI, unemployment) with seasonal structure.",
        "Energy-load forecasting where defensible intervals matter.",
    ],
    "ols": [
        "The default tool of empirical economics: wage gaps, policy effects, demand elasticities.",
        "Any report where a coefficient must carry a confidence interval.",
    ],
    "logit": [
        "Labour economics: probability of employment/participation.",
        "Credit and insurance underwriting with odds-ratio reporting.",
    ],
    "probit": [
        "Discrete-choice models in economics (buy/don't-buy, adopt/don't).",
        "Standard in finance for default studies following the latent-score story.",
    ],
    "poisson": [
        "Insurance claim counts per policy-year (with exposure offsets).",
        "Patent counts, hospital visits, accident counts in applied econ.",
    ],
    "arima": [
        "Short-horizon financial and operations series without seasonality.",
        "Baseline forecasts that anchor fancier models' evaluation.",
    ],
    "rdd": ["Scholarship/aid effects at a test-score cutoff.", "Incumbency advantage at the 50% vote share."],
    "ar": ["Short-term demand from recent demand.", "Interest-rate persistence modelling."],
    "ma": ["Smoothing noisy sensor/price series.", "Modelling shock-driven series (news effects)."],
    "arma": ["Stationary macro series (detrended GDP growth).", "Baseline for Box–Jenkins forecasting."],
    "vecm": ["Spot vs futures prices (they never drift apart).", "Money, prices and output in macro."],
    "egarch": ["Equity-index volatility with leverage.", "Risk models needing asymmetric response."],
    "gjr_garch": ["Stock-return volatility with downside kicks.", "VaR where crashes matter most."],
    "multinomial_logit": ["Travel-mode choice (car/bus/train).", "Brand choice in marketing."],
    "ordered_logit": ["Credit-rating models (AAA…D).", "Survey satisfaction (1–5) drivers."],
    "ordered_probit": ["Bond-rating models.", "Ordinal health-status regressions."],
    "wls": ["Grouped/aggregated data where group sizes differ.", "Survey data with known design weights."],
    "gls": ["Time-series regressions with autocorrelated errors.", "Panel error structures."],
    "robust": ["Wage or price regressions with a few extreme outliers.", "Sensor data with glitches."],
    "zip": ["Doctor-visit counts with many non-users.", "Purchase counts with many never-buyers."],
    "quantile": [
        "Wage-gap studies across the earnings distribution (glass-ceiling effects at the top).",
        "Value-at-Risk and growth-at-risk in finance (modelling the bad tail directly).",
    ],
    "negative_binomial": [
        "Insurance claim counts with overdispersion; hospital admissions.",
        "Crime counts per district, patent counts per firm.",
    ],
    "arch": [
        "Early volatility forecasting for risk desks (the model that won Engle the Nobel).",
        "Teaching baseline before GARCH in any econometrics course.",
    ],
    "garch": [
        "Value-at-Risk and expected shortfall on trading books.",
        "Option pricing and dynamic hedging; volatility targeting in funds.",
    ],
    "var": [
        "Central-bank macro models: how a rate shock ripples into GDP and inflation.",
        "Modelling co-moving asset returns and their spillovers.",
    ],
    "rct": [
        "Tech A/B tests (button colour, pricing, recommendations).",
        "Development economics field experiments; clinical trials.",
    ],
    "did": [
        "The Card–Krueger minimum-wage study (the canonical DiD).",
        "Evaluating a policy rollout, merger, or law that hit some states/firms and not others.",
    ],
    "iv": [
        "Returns to schooling using distance-to-college as the instrument (Card).",
        "Demand estimation with cost shifters as instruments for price.",
    ],
    "pooled_ols": [
        "First-pass wage regressions on worker-year panels.",
        "Cross-country growth regressions before adding country effects.",
    ],
    "fixed_effects": [
        "Minimum-wage / policy studies: the same state before vs after.",
        "Firm-year panels: does R&D raise productivity WITHIN a firm?",
    ],
    "random_effects": [
        "Household survey panels (income dynamics) where entities are sampled draws.",
        "Multilevel education studies: students within schools.",
    ],
}

EDGE_CASES: dict[str, list[str]] = {
    "xgboost": [
        "Missing values: handled natively — each split learns a default direction for NaNs.",
        "Extrapolation: predictions PLATEAU outside the training range (trees can't extend a trend).",
        "Heavy class imbalance: tune scale_pos_weight or the threshold, not just accuracy.",
    ],
    "gradient_boosting": [
        "Noisy labels: boosting chases every residual — cap depth, lower the learning rate.",
        "Same extrapolation plateau as all trees.",
    ],
    "decision_tree": [
        "Tiny data changes can flip the whole tree (high variance) — don't over-read one tree.",
        "Axis-aligned splits struggle with diagonal boundaries.",
    ],
    "random_forest": [
        "Feature importances are biased toward high-cardinality features — prefer permutation importance.",
        "Cannot predict beyond the training range (no trend extrapolation).",
    ],
    "extra_trees": [
        "Random thresholds need a few more trees to stabilise than a forest.",
        "Same importance-bias and extrapolation caveats as random forest.",
    ],
    "adaboost": [
        "A few mislabelled rows can dominate: their weights explode round after round.",
        "Not robust to heavy noise — check the weight distribution.",
    ],
    "bagging": [
        "Averaging can't fix a biased base model — it only calms variance.",
        "Bootstrap duplicates rows: leakage if 'duplicates' are really the same entity.",
    ],
    "logistic_regression": [
        "Perfect separation makes weights run to infinity — regularise or use penalised fits.",
        "Unscaled features slow/destabilise the optimiser and distort penalties.",
    ],
    "linear_regression": [
        "One extreme outlier can drag the whole line (squared loss).",
        "Collinear features make individual coefficients meaningless even when fit is fine.",
    ],
    "ridge": [
        "Coefficients are biased — don't read them as causal effect sizes.",
        "Pick α by cross-validation; the 'best' α changes with scaling.",
    ],
    "lasso": [
        "With correlated features it keeps ONE arbitrarily — the dropped ones aren't 'irrelevant'.",
        "When p > n it can select at most n features.",
    ],
    "elastic_net": [
        "Two knobs interact: tune α and l1_ratio jointly, not one at a time.",
        "Still linear — engineered interactions are on you.",
    ],
    "knn": [
        "Forget to scale and one big-unit feature decides everything.",
        "High dimensions: all distances converge — neighbours stop being 'near'.",
    ],
    "svm": [
        "RBF without scaling is broken by construction.",
        "Probabilities come from an extra calibration step, not the margin.",
    ],
    "naive_bayes": [
        "Correlated features double-count evidence → overconfident probabilities.",
        "Unseen category values need smoothing or they zero the whole product.",
    ],
    "mlp": [
        "Unscaled inputs stall training; always standardise.",
        "Different random seeds give different nets — report averages.",
    ],
    "gaussian_process": [
        "O(n³): a few thousand rows is the ceiling.",
        "The kernel IS the assumption — a wrong kernel gives confident nonsense.",
    ],
    "cnn": [
        "Shuffling column order destroys it — locality is the whole point.",
        "Small datasets overfit fast: augment or transfer-learn.",
    ],
    "rnn": [
        "Plain RNN cells forget quickly (vanishing gradients) — default to LSTM/GRU.",
        "Never shuffle time order; validate on the FUTURE, not a random split.",
    ],
    "transformer": [
        "O(n²) attention blows up on long sequences.",
        "Small-data regimes underperform trees/LSTMs badly.",
    ],
    "kmeans": [
        "Must scale features; k-means with unscaled money columns clusters by income only.",
        "Non-round clusters (moons/rings) get cut through the middle.",
        "Every point is forced into a cluster — outliers distort centroids.",
    ],
    "dbscan": [
        "One ε cannot fit clusters of different densities.",
        "In high dimensions density loses meaning — reduce dimensions first.",
    ],
    "gmm": [
        "EM finds local optima — run several initialisations.",
        "Full covariance eats parameters; use 'diag' on small data.",
    ],
    "hierarchical": [
        "Single linkage chains distinct groups together through one bridge point.",
        "O(n²) memory: sample before clustering big data.",
    ],
    "spectral": [
        "The similarity graph's σ/affinity choice silently decides the answer.",
        "Eigen-decomposition cost limits it to small n.",
    ],
    "isolation_forest": [
        "Scores are relative — 'contamination' converts them to alerts, and that's a guess.",
        "Local anomalies inside dense regions slip through.",
    ],
    "lof": [
        "k too small → everything looks anomalous; too large → local structure blurs.",
        "Scores aren't comparable across datasets.",
    ],
    "one_class_svm": [
        "Anomalies hiding in the training data poison the boundary.",
        "ν and γ interact — tune together.",
    ],
    "ets": [
        "Wrong seasonal_periods (12 vs 7) silently learns garbage seasonality.",
        "Structural breaks (policy changes, pandemics) — retrain from the break.",
    ],
    "sarima": [
        "Forgetting to difference (d) leaves trends in residuals — check stationarity first.",
        "Prediction intervals assume the pattern persists; regime changes void them.",
    ],
    "ols": [
        "Heteroskedastic errors: coefficients fine, plain SEs wrong — use robust SEs.",
        "Omitted-variable bias: a missing confounder poisons causal readings.",
        "R² never falls when adding junk — use adjusted R² / out-of-sample checks.",
    ],
    "logit": [
        "Perfect separation → infinite coefficients (Firth/penalised logit).",
        "Coefficients are on the log-odds scale — report marginal effects for probabilities.",
    ],
    "probit": [
        "No odds-ratio shortcut — interpretation is via marginal effects only.",
        "Same separation issue as logit.",
    ],
    "poisson": [
        "Overdispersion (variance >> mean) is the norm — test it; use negative binomial.",
        "Excess zeros need zero-inflated models; don't forget the exposure offset.",
    ],
    "arima": [
        "Over-differencing introduces artificial MA structure.",
        "AIC-chasing tiny order changes overfits the sample.",
    ],
    "rdd": ["Manipulation of the running variable near the cutoff (bunching) invalidates it.",
            "Effect is LOCAL to the cutoff — don't extrapolate far from it."],
    "ar": ["Non-stationary input gives spurious fits — difference first.",
           "Too-high p overfits; the PACF should guide it."],
    "ma": ["Invertibility issues if q is too high.", "Needs stationarity like AR."],
    "arma": ["Over-parameterising (both p and q large) overfits.", "Requires a stationary series."],
    "vecm": ["Wrong cointegration rank misleads badly — test it (Johansen).",
             "Assumes LINEAR adjustment to equilibrium."],
    "egarch": ["More parameters → needs more data to estimate stably.",
               "Still Gaussian by default; add Student-t for tails."],
    "gjr_garch": ["Only one asymmetry threshold (at zero).", "Gaussian tails understate risk."],
    "multinomial_logit": ["IIA assumption often fails (red-bus/blue-bus).",
                          "Many categories → many parameters, unstable on small data."],
    "ordered_logit": ["Proportional-odds assumption can fail — test it.",
                     "Treats category distances as unknown, only their order."],
    "ordered_probit": ["No odds-ratio reading — interpret marginal effects.",
                      "Same threshold assumptions as ordered logit."],
    "wls": ["Wrong weights can be WORSE than OLS + robust SEs.",
            "Weights are usually unknown and must be estimated (FGLS)."],
    "gls": ["The error covariance is rarely known — misspecification hurts.",
            "Heavy to estimate for large samples."],
    "robust": ["Down-weights y-outliers but not high-leverage x-points.",
               "Less efficient than OLS on clean data."],
    "zip": ["If counts are also overdispersed, use zero-inflated NB, not ZIP.",
            "Needs a story for the structural-zero process."],
    "quantile": [
        "Fitted quantile lines can CROSS on small samples — a sign to fit fewer, or more data.",
        "The median fit ignores the mean entirely — don't compare its coefficients to OLS naively.",
    ],
    "negative_binomial": [
        "If the data ISN'T overdispersed, Poisson is more efficient — test first.",
        "Excess zeros still break it; reach for zero-inflated / hurdle models.",
    ],
    "arch": [
        "Symmetric: it can't capture the leverage effect (crashes spike vol more than rallies).",
        "Often needs many lags — GARCH captures the same persistence with two parameters.",
    ],
    "garch": [
        "α+β must be < 1 for a stationary variance; near 1 means shocks barely decay (IGARCH).",
        "Gaussian errors understate fat tails — use Student-t for real risk numbers.",
        "Fit on RETURNS, not prices; scale to ~% or the optimiser struggles.",
    ],
    "var": [
        "Parameters grow with (series × lags)² — keep both small or estimates are noisy.",
        "Non-stationary series need differencing or a VECM, or the VAR is spurious.",
    ],
    "rct": [
        "Non-compliance and attrition break the clean comparison — analyse intention-to-treat.",
        "Randomisation balances IN EXPECTATION; check covariate balance on your actual sample.",
    ],
    "did": [
        "Parallel trends is the whole ballgame — plot pre-treatment trends; it's untestable after.",
        "Staggered rollouts + heterogeneous effects bias classic two-way FE DiD (use new estimators).",
    ],
    "iv": [
        "Weak instrument (first-stage F < 10): estimates are badly biased toward OLS and imprecise.",
        "The exclusion restriction (instrument affects Y only through X) is an untestable assumption.",
        "IV estimates a LOCAL effect for compliers (LATE) — not the average for everyone.",
    ],
    "pooled_ols": [
        "Rows within an entity are correlated — plain SEs are too small; cluster by entity.",
        "A single heavy entity can dominate the pooled fit.",
    ],
    "fixed_effects": [
        "Time-constant variables (gender, geography) cannot be estimated — they demean to zero.",
        "Measurement error is AMPLIFIED by the within transform (little signal left).",
    ],
    "random_effects": [
        "If entity effects correlate with X, RE is biased — always report the Hausman test.",
        "Few entities (<20) make the variance components unreliable.",
    ],
}

EXAM_QA: dict[str, list[tuple[str, str]]] = {
    "xgboost": [
        ("Derive the optimal leaf value.",
         "Second-order Taylor of the loss in the leaf value w gives Σ(gw + ½hw²) + ½λw²; "
         "setting the derivative to zero yields w* = −Σg/(Σh+λ)."),
        ("Why does the similarity score use (Σg)² rather than Σg?",
         "Plugging w* back into the quadratic shows the loss reduction is ½(Σg)²/(Σh+λ); the "
         "square also rewards groups whose gradients AGREE (they stack instead of cancel)."),
        ("Does XGBoost try every possible split point?",
         "Exact mode does per feature; in practice it uses quantile sketches — a short list of "
         "candidate thresholds per feature — which is what the auditions showed."),
        ("What do λ and γ regularise, respectively?",
         "λ shrinks similarity scores and leaf values (L2 on leaf weights); γ is a fixed toll "
         "per split — any split whose gain can't pay it is pruned."),
    ],
    "gradient_boosting": [
        ("Why is it called GRADIENT boosting?",
         "Each new tree is fit to the negative gradient of the loss at the current prediction "
         "— for squared error that gradient IS the residual."),
        ("Boosting vs bagging in one sentence each?",
         "Bagging trains independent models in parallel and averages to cut VARIANCE; boosting "
         "trains sequentially on what's still wrong to cut BIAS."),
    ],
    "decision_tree": [
        ("Compute the gini of a node with 6 'yes' and 2 'no'.",
         "p = 0.75/0.25 → gini = 1 − (0.75² + 0.25²) = 1 − 0.625 = 0.375."),
        ("Why do deep trees overfit?",
         "With enough depth each leaf can isolate single rows — training error hits zero while "
         "the rules memorise noise that won't repeat out of sample."),
    ],
    "random_forest": [
        ("Why must the trees be DECORRELATED, and how does the forest do it?",
         "Averaging only cuts variance if the errors differ; bootstrap rows + random feature "
         "menus per split make the trees disagree in different ways."),
        ("What is OOB error?",
         "Each tree skips ~37% of rows (out-of-bag); predicting those with the trees that "
         "never saw them gives a free cross-validation estimate."),
    ],
    "extra_trees": [
        ("What exactly is 'extra' random vs a random forest?",
         "Split thresholds are drawn at random instead of searched exhaustively — cheaper per "
         "split and even more decorrelated trees."),
    ],
    "adaboost": [
        ("What does a stump's 'say' α = ½ln((1−ε)/ε) do at ε = 0.5?",
         "α = 0 — a coin-flip stump gets zero voice; the better than random it is, the louder "
         "its vote."),
        ("Why is AdaBoost outlier-sensitive?",
         "Repeatedly misclassified rows have their weights multiplied every round, so a "
         "mislabelled outlier eventually dominates training."),
    ],
    "bagging": [
        ("What share of rows does each bootstrap sample leave out?",
         "About 1/e ≈ 37% — those out-of-bag rows enable free validation."),
    ],
    "logistic_regression": [
        ("Why not fit a straight line to a 0/1 outcome?",
         "The linear probability model predicts outside [0,1] and has non-constant variance; "
         "the sigmoid keeps outputs valid and log-loss handles the errors properly."),
        ("Interpret a weight of 0.7 on 'years of education'.",
         "Each extra year adds 0.7 to the log-odds, multiplying the odds by e^0.7 ≈ 2.0."),
    ],
    "linear_regression": [
        ("What does 'least squares' minimise and why squared?",
         "The sum of squared residuals; squaring penalises big misses more, keeps the maths "
         "differentiable, and gives the closed-form solution."),
        ("What does R² = 0.65 mean?",
         "65% of the outcome's variance is explained by the fitted line; 35% remains."),
    ],
    "ridge": [
        ("Why does ridge help with collinearity?",
         "Correlated features make the unpenalised solution ill-conditioned (huge offsetting "
         "weights); the L2 penalty makes the problem well-posed and shares weight among them."),
    ],
    "lasso": [
        ("Why does L1 zero coefficients while L2 doesn't?",
         "The L1 constraint region has corners on the axes; the loss contours usually touch a "
         "corner, where some coefficients are exactly zero. The L2 ball is round — no corners."),
    ],
    "elastic_net": [
        ("When does elastic net beat plain lasso?",
         "With groups of correlated predictors: lasso picks one arbitrarily, elastic net "
         "brings the group in together while staying sparse."),
    ],
    "knn": [
        ("What happens at k = 1 and k = n?",
         "k=1 memorises (zero train error, jagged boundary); k=n predicts the global majority/"
         "mean for everyone — maximum smoothing."),
        ("Why does k-NN degrade in high dimensions?",
         "Distances concentrate: nearest and farthest points become nearly equidistant, so "
         "'nearest' carries no information (curse of dimensionality)."),
    ],
    "svm": [
        ("Define support vectors.",
         "The training points on or inside the margin — the only points that determine the "
         "boundary; delete the rest and nothing moves."),
        ("What is the kernel trick?",
         "Computing inner products in a high-dimensional feature space directly via a kernel "
         "function, without ever constructing the mapped features."),
    ],
    "naive_bayes": [
        ("State the 'naive' assumption and why it still works.",
         "Features are conditionally independent given the class. The probabilities are "
         "miscalibrated when it fails, but the ARGMAX (the predicted class) is often still "
         "right."),
    ],
    "mlp": [
        ("Why do we need non-linear activations at all?",
         "Stacked linear layers collapse to one linear map; the squash between layers is what "
         "lets the network represent curves and interactions."),
        ("What does backpropagation actually compute?",
         "The gradient of the loss w.r.t. every weight, via the chain rule applied layer by "
         "layer backwards — then the optimiser steps each weight against it."),
    ],
    "gaussian_process": [
        ("What does the kernel encode?",
         "Similarity between inputs — and through it, assumptions like smoothness and "
         "length-scale of the function being learned."),
    ],
    "cnn": [
        ("Why convolution instead of a dense layer on an image?",
         "Weight sharing: one small detector slides everywhere, so the pattern is learned once "
         "regardless of position, with far fewer parameters."),
        ("What does max-pooling contribute?",
         "Keeps the strongest local evidence while shrinking the map — small translation "
         "invariance plus compute savings."),
    ],
    "rnn": [
        ("Name the three LSTM gates and their jobs.",
         "Forget (what to erase from cell state), input (what new information to write), "
         "output (what part of the memory to reveal as the hidden state)."),
        ("Why do plain RNNs 'forget'?",
         "Backprop through time multiplies many small derivatives — gradients vanish, so "
         "long-range influences can't be learned."),
    ],
    "transformer": [
        ("Why divide by √d in attention?",
         "Dot products grow with dimension; scaling keeps the softmax from saturating so "
         "gradients stay useful."),
        ("What problem does multi-head attention solve over single-head?",
         "Each head learns a DIFFERENT who-listens-to-whom pattern (syntax vs topic vs "
         "position), then their views are concatenated."),
    ],
    "kmeans": [
        ("Why does Lloyd's algorithm always terminate?",
         "Both steps (assign, move-to-mean) can only lower the inertia, which is bounded "
         "below — so it converges (possibly to a local optimum)."),
        ("How do you choose k?",
         "Elbow on inertia, silhouette score, or domain constraints — inertia alone always "
         "improves with k, so never read it raw."),
    ],
    "dbscan": [
        ("Define core, border, and noise points.",
         "Core: ≥ min_samples neighbours within ε. Border: within ε of a core but not core "
         "itself. Noise: neither — left unclustered."),
    ],
    "gmm": [
        ("What do the E and M steps do?",
         "E: compute each point's responsibilities (soft membership) under current gaussians; "
         "M: re-fit each gaussian's mean/covariance/weight from those responsibilities."),
    ],
    "hierarchical": [
        ("Ward vs single linkage — expected cluster shapes?",
         "Ward merges to minimise within-cluster variance (compact blobs); single linkage "
         "merges nearest points (chains and elongated clusters)."),
    ],
    "spectral": [
        ("Why embed with eigenvectors before clustering?",
         "The graph Laplacian's leading eigenvectors place weakly-connected components far "
         "apart, turning tangled shapes into separable blobs for k-means."),
    ],
    "isolation_forest": [
        ("Why do anomalies have SHORT paths?",
         "A point far from the crowd is separated by a random cut early; dense-crowd points "
         "need many cuts before they're alone."),
    ],
    "lof": [
        ("A point has LOF ≈ 1. Interpretation?",
         "Its local density matches its neighbours' — ordinary. LOF >> 1 means much sparser "
         "than its neighbourhood — a local outlier."),
    ],
    "one_class_svm": [
        ("What does ν control?",
         "An upper bound on the fraction of training points outside the boundary (and a lower "
         "bound on the fraction of support vectors) — the wrap's looseness."),
    ],
    "ets": [
        ("What does α close to 1 vs close to 0 mean?",
         "Near 1: memory is short — the level chases the latest observation. Near 0: long "
         "memory — the level barely moves on new data."),
    ],
    "sarima": [
        ("How do ACF/PACF suggest q and p?",
         "A sharp PACF cutoff at lag p suggests AR(p); a sharp ACF cutoff at lag q suggests "
         "MA(q); slow ACF decay suggests differencing first."),
        ("What does d = 1 do and why?",
         "Model the CHANGES (yₜ − yₜ₋₁) instead of levels, removing a stochastic trend so the "
         "AR/MA machinery sees a stationary series."),
    ],
    "ols": [
        ("Interpret a p-value of 0.03 on a coefficient.",
         "If the true effect were zero, data this extreme would appear only 3% of the time — "
         "evidence (not proof) of a real association."),
        ("State the Gauss–Markov conditions in plain words.",
         "Linear model, exogenous errors (mean zero given X), constant error variance, no "
         "perfect collinearity — then OLS is the best linear unbiased estimator."),
        ("Why can adding a variable FLIP another coefficient's sign?",
         "Omitted-variable bias: the old coefficient absorbed the confounder's effect; "
         "controlling for it re-attributes the variation."),
    ],
    "logit": [
        ("Convert β = 0.29 on education into an odds ratio and interpret.",
         "e^0.29 ≈ 1.34: each extra year multiplies the odds of the outcome by 1.34 — a 34% "
         "increase in odds, NOT in probability."),
        ("Marginal effect vs coefficient?",
         "The coefficient moves the log-odds; the marginal effect (β·p·(1−p) at a point) is "
         "the change in PROBABILITY — what policy audiences usually want."),
    ],
    "probit": [
        ("Write the probit model's story.",
         "y* = Xβ + ε with ε ~ N(0,1); we observe y = 1 when the latent score y* crosses 0 — "
         "so P(y=1) = Φ(Xβ)."),
        ("Logit vs probit — practical difference?",
         "Nearly identical fits; logit has slightly fatter tails and odds-ratio "
         "interpretability, probit matches the latent-normal framing. Field convention "
         "usually decides."),
    ],
    "poisson": [
        ("Why is E[y] = Var[y] both the model's core and its weakness?",
         "The Poisson distribution forces mean = variance; real counts usually spread wider "
         "(overdispersion), understating standard errors — hence negative binomial."),
        ("Interpret e^β = 1.15 on 'store promotions'.",
         "Each additional promotion multiplies the expected COUNT (the rate) by 1.15 — a 15% "
         "rate increase, holding the rest fixed."),
    ],
    "arima": [
        ("What are the three parts of ARIMA(p,d,q)?",
         "AR(p): p lagged values; I(d): difference the series d times to stationarity; MA(q): "
         "q lagged forecast errors."),
    ],
    "rdd": [
        ("Why is the jump at the cutoff causal?",
         "Units just above and just below the threshold are essentially identical except for "
         "treatment, so the discontinuity in the outcome isolates the treatment's effect."),
        ("Sharp vs fuzzy RDD?",
         "Sharp: treatment switches deterministically at the cutoff. Fuzzy: the cutoff only "
         "CHANGES THE PROBABILITY of treatment, so you scale the jump by the first-stage jump (IV)."),
    ],
    "ar": [("How does the PACF reveal the AR order?",
            "The partial autocorrelation cuts off after lag p for an AR(p) process — a sharp drop "
            "to zero at lag p+1.")],
    "ma": [("How does the ACF reveal the MA order?",
            "The autocorrelation cuts off after lag q for an MA(q) process.")],
    "arma": [("How do you pick p and q for ARMA?",
              "Read the ACF (for q) and PACF (for p), then compare candidate models by AIC/BIC and "
              "check the residuals are white noise.")],
    "vecm": [("What is the error-correction term?",
              "The lagged deviation from the long-run equilibrium; its coefficient says how fast "
              "each series pulls back when the relationship is stretched.")],
    "egarch": [("Why does EGARCH need no positivity constraints?",
                "It models the LOG of variance, which can be any sign, so the exponential of it is "
                "always positive — no parameter restrictions required.")],
    "gjr_garch": [("How does GJR capture the leverage effect?",
                   "An extra term multiplies yesterday's squared shock by an indicator for negative "
                   "returns, adding EXTRA variance after bad news.")],
    "multinomial_logit": [("State the IIA assumption and a case where it fails.",
                           "The odds between two alternatives don't depend on other alternatives. "
                           "It fails in the red-bus/blue-bus problem, where a near-duplicate option "
                           "steals share disproportionately.")],
    "ordered_logit": [("What is the proportional-odds assumption?",
                       "The effect of each predictor is the SAME across all category thresholds — "
                       "one slope, several cut-points. Violations need a generalized ordered model.")],
    "ordered_probit": [("How does the latent-variable story work for ordered probit?",
                        "A hidden normal score y* = Xβ + ε crosses a series of cut-points; which "
                        "interval it lands in gives the observed ordered category.")],
    "wls": [("How does WLS relate to OLS and GLS?",
             "WLS is GLS with a DIAGONAL error covariance (heteroskedastic but uncorrelated); OLS "
             "is WLS with equal weights.")],
    "gls": [("When does GLS reduce to OLS?",
             "When the error covariance is a scalar times the identity — homoskedastic, "
             "uncorrelated errors — GLS and OLS coincide.")],
    "robust": [("How does Huber M-estimation resist outliers?",
                "It uses squared loss for small residuals but switches to LINEAR loss beyond a "
                "threshold, so far outliers get bounded (not squared) influence.")],
    "zip": [("What two processes does a zero-inflated Poisson combine?",
             "A binary process generating STRUCTURAL zeros (never-events) and a Poisson count "
             "process that itself can also produce zeros — mixed together.")],
    "quantile": [
        ("What loss does quantile regression minimise?",
         "The pinball (check) loss: it weights over- and under-predictions asymmetrically by the "
         "quantile q, so the minimiser is the qth conditional quantile."),
        ("Why is the median regression robust to outliers but OLS isn't?",
         "OLS minimises SQUARED errors, so a far outlier dominates; the median minimises ABSOLUTE "
         "errors, where one extreme point counts the same as any other."),
    ],
    "negative_binomial": [
        ("What does the dispersion parameter add over Poisson?",
         "Poisson forces variance = mean; the negative binomial adds a parameter letting variance "
         "= mean + α·mean², absorbing overdispersion and fixing the too-small standard errors."),
    ],
    "arch": [
        ("Write the ARCH(1) variance equation and read it.",
         "σ²_t = ω + α·ε²_(t−1): today's variance is a baseline plus a fraction of yesterday's "
         "SQUARED shock — so a big move (either sign) raises tomorrow's expected volatility."),
    ],
    "garch": [
        ("Write GARCH(1,1) and interpret α+β.",
         "σ²_t = ω + α·ε²_(t−1) + β·σ²_(t−1). α is the reaction to new shocks, β the persistence "
         "of old variance; α+β (near 1) is how slowly volatility mean-reverts."),
        ("Why does GARCH beat a high-order ARCH?",
         "The β·σ²_(t−1) term folds in ALL past squared shocks geometrically, so GARCH(1,1) "
         "matches long persistence that would need many ARCH lags — parsimony."),
        ("What is the leverage effect and which model captures it?",
         "Negative returns raise volatility more than equal positive ones; symmetric GARCH misses "
         "it — EGARCH or GJR-GARCH add an asymmetry term."),
    ],
    "var": [
        ("What is an impulse-response function?",
         "It traces how a one-time shock to one series moves every series over the following "
         "periods, holding the estimated dynamics fixed — the main output people read from a VAR."),
        ("What does Granger causality mean here?",
         "X Granger-causes Y if X's past helps predict Y beyond Y's own past — a predictive, not "
         "structural, notion of causality that VARs test directly."),
    ],
    "rct": [
        ("Why does randomisation license a simple difference in means?",
         "Random assignment makes treatment independent of ALL confounders (observed or not), so "
         "the groups are comparable in expectation and the mean gap is the average treatment effect."),
        ("Intention-to-treat vs per-protocol — which preserves the randomisation?",
         "Intention-to-treat: analyse people by their ASSIGNED group regardless of compliance. "
         "Per-protocol conditions on behaviour and reintroduces selection bias."),
    ],
    "did": [
        ("State the DiD estimator and its key assumption.",
         "effect = (treated_post − treated_pre) − (control_post − control_pre). It assumes "
         "PARALLEL TRENDS: absent treatment, both groups would have moved the same way."),
        ("Why subtract the control's change at all?",
         "To net out the common time trend and any shock that hit both groups, isolating what the "
         "treatment ADDED beyond what would have happened anyway."),
    ],
    "iv": [
        ("Name the two conditions a valid instrument must satisfy.",
         "Relevance: it must actually move the endogenous regressor (strong first stage). "
         "Exclusion: it must affect the outcome ONLY through that regressor, not directly."),
        ("Walk through the two stages of 2SLS.",
         "Stage 1: regress the endogenous X on the instrument to get the exogenous part X̂. "
         "Stage 2: regress Y on X̂ — the variation left is instrument-driven, so the coefficient "
         "is causal."),
        ("What does a first-stage F below 10 warn you about?",
         "A weak instrument: the 2SLS estimate is biased toward the confounded OLS and its "
         "standard errors are unreliable."),
    ],
    "pooled_ols": [
        ("Why must pooled-OLS standard errors be clustered by entity?",
         "Observations of the same entity share unobserved shocks, so they aren't independent; "
         "treating them as independent overstates the effective sample size and shrinks SEs."),
    ],
    "fixed_effects": [
        ("Why does FE remove time-constant confounders — show the algebra idea.",
         "yᵢₜ = βxᵢₜ + αᵢ + εᵢₜ; subtracting entity means gives (yᵢₜ−ȳᵢ) = β(xᵢₜ−x̄ᵢ) + "
         "(εᵢₜ−ε̄ᵢ): the αᵢ term — everything constant within entity i — cancels exactly."),
        ("Why can't FE estimate the effect of gender or region?",
         "Those variables never change within an entity, so their demeaned values are zero — "
         "there's no within variation left to identify a coefficient."),
    ],
    "random_effects": [
        ("State the RE assumption and the test for it.",
         "The entity effects αᵢ are uncorrelated with the regressors. The Hausman test "
         "compares FE and RE estimates: a large difference rejects RE in favour of FE."),
        ("Why is RE more efficient than FE when valid?",
         "RE uses BOTH within- and between-entity variation (a weighted average), while FE "
         "discards all between variation — so RE's standard errors are smaller."),
    ],
}


def enrich() -> None:
    """Apply the drill content onto the registered ModelFacts (idempotent)."""
    for key, apps in APPLICATIONS.items():
        if key in FACTS:
            FACTS[key].applications = list(apps)
    for key, edges in EDGE_CASES.items():
        if key in FACTS:
            FACTS[key].edge_cases = list(edges)
    for key, qas in EXAM_QA.items():
        if key in FACTS:
            FACTS[key].exam_questions = [ExamQA(q=q, a=a) for q, a in qas]
