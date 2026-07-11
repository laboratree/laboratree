"""Curated facts for Wave-2 econometrics/stats/finance models (14)."""

from __future__ import annotations

from . import Alternative, HyperparameterDoc, ModelFacts, register_facts


def _a(model: str, when: str) -> Alternative:
    return Alternative(model=model, prefer_when=when)


def _h(name: str, plain: str, effect: str, rng: str = "") -> HyperparameterDoc:
    return HyperparameterDoc(name=name, plain=plain, effect=effect, typical_range=rng)


register_facts(ModelFacts(
    key="rdd", display_name="Regression Discontinuity", family="linear",
    one_liner="The jump in the outcome at a treatment cutoff is the causal effect.",
    pros=["Near-experimental credibility when treatment switches at a sharp threshold",
          "Transparent and visual — you can literally SEE the jump",
          "Weak assumptions: only local continuity of everything else at the cutoff"],
    cons=["Estimates a LOCAL effect right at the cutoff — poor external validity",
          "Bandwidth choice trades bias against variance", "Needs lots of data near the cutoff"],
    limitations=["Manipulation of the running variable around the cutoff invalidates it"],
    use_when=["A rule assigns treatment by a score crossing a threshold (scholarships, subsidies)."],
    alternatives=[_a("RCT", "you can randomise instead"),
                  _a("Difference-in-Differences", "treatment is a group×time event, not a cutoff")],
    hyperparameters=[_h("bandwidth", "How far from the cutoff to include.",
                        "Narrow = less bias, more variance; wide = the opposite.", "data-specific")],
))

register_facts(ModelFacts(
    key="ar", display_name="AR (autoregressive)", family="timeseries",
    one_liner="Today from its own recent past values — the AR piece of ARIMA.",
    pros=["Simplest memory model; interpretable coefficients", "PACF reads the order p directly"],
    cons=["Needs a stationary series", "Only linear dependence on the past"],
    limitations=["Ignores moving-average (error) structure"],
    use_when=["A stationary series where recent LEVELS drive the next value."],
    alternatives=[_a("ARMA", "past ERRORS also matter"), _a("ARIMA", "the series has a trend to difference")],
    hyperparameters=[_h("order", "How many past values (p).", "Read it from the PACF cutoff.", "1–3")],
))

register_facts(ModelFacts(
    key="ma", display_name="MA (moving average)", family="timeseries",
    one_liner="Today from recent forecast errors — the MA piece of ARIMA.",
    pros=["Captures short shocks that decay quickly", "ACF reads the order q directly"],
    cons=["Less intuitive than AR (it's about errors, not levels)", "Needs stationarity"],
    limitations=["Pure MA is rare; usually combined with AR"],
    use_when=["A series where yesterday's SURPRISE, not its level, moves today."],
    alternatives=[_a("AR", "past levels drive the series"), _a("ARMA", "both matter")],
    hyperparameters=[_h("order", "How many past errors (q).", "Read it from the ACF cutoff.", "1–3")],
))

register_facts(ModelFacts(
    key="arma", display_name="ARMA", family="timeseries",
    one_liner="Past values AND past errors on a stationary series.",
    pros=["Flexible: covers most stationary short-memory dynamics parsimoniously",
          "The core of ARIMA/SARIMA"],
    cons=["Order selection (p,q) takes judgement", "Requires stationarity"],
    limitations=["No trend or seasonality without the I and S extensions"],
    use_when=["A stationary series with both autoregressive and shock dynamics."],
    alternatives=[_a("ARIMA", "there's a trend to difference away"),
                  _a("SARIMA", "there's a seasonal cycle")],
    hyperparameters=[_h("p", "AR order.", "From the PACF.", "0–3"),
                     _h("q", "MA order.", "From the ACF.", "0–3")],
))

register_facts(ModelFacts(
    key="vecm", display_name="VECM (cointegration)", family="timeseries",
    one_liner="Non-stationary series that share a long-run equilibrium and correct back to it.",
    pros=["Models both short-run dynamics AND the long-run equilibrium relationship",
          "The right tool when series are individually non-stationary but move together",
          "The error-correction term shows how fast they revert"],
    cons=["Requires establishing cointegration first (Johansen test)",
          "More involved to specify than a plain VAR"],
    limitations=["Wrong cointegration rank misleads; assumes linear adjustment"],
    use_when=["Prices/rates that wander individually but never drift far apart (spot & futures)."],
    alternatives=[_a("VAR in differences", "the series are NOT cointegrated"),
                  _a("VAR", "the series are already stationary")],
    hyperparameters=[_h("lags", "Short-run lag order.", "More lags capture richer dynamics.", "1–3")],
))

register_facts(ModelFacts(
    key="egarch", display_name="EGARCH", family="timeseries",
    one_liner="GARCH with the leverage effect — bad news raises volatility more.",
    pros=["Captures ASYMMETRY (leverage): crashes spike vol more than rallies",
          "Models log-variance, so no positivity constraints on parameters"],
    cons=["Harder to interpret than plain GARCH", "More parameters to estimate"],
    limitations=["Still Gaussian by default; fat tails want Student-t"],
    use_when=["Equity/index returns, where downside shocks clearly hit volatility harder."],
    alternatives=[_a("GARCH", "volatility responds symmetrically"),
                  _a("GJR-GARCH", "you want a simpler asymmetry term")],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="gjr_garch", display_name="GJR-GARCH", family="timeseries",
    one_liner="GARCH plus an asymmetry term for downside shocks.",
    pros=["Adds ONE term to GARCH to capture the leverage effect",
          "Easy to interpret: an extra kick to variance after negative returns"],
    cons=["Still symmetric baseline plus one asymmetry term", "Gaussian tails understate risk"],
    limitations=["Assumes stationarity; one threshold at zero"],
    use_when=["Equity returns where you want leverage without EGARCH's log machinery."],
    alternatives=[_a("EGARCH", "you prefer modelling log-variance"),
                  _a("GARCH", "no meaningful asymmetry in your series")],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="multinomial_logit", display_name="Multinomial Logit", family="linear",
    one_liner="Unordered categorical choice — brand, transport mode.",
    pros=["Handles 3+ unordered outcomes with interpretable relative-risk ratios",
          "Fast, standard, well understood"],
    cons=["Assumes IIA (independence of irrelevant alternatives) — often violated",
          "One coefficient set PER alternative gets unwieldy with many categories"],
    limitations=["Ignores any ordering in the categories"],
    use_when=["Choosing among unordered options: which product, which mode, which party."],
    alternatives=[_a("Ordered logit", "the categories have a natural order"),
                  _a("Nested / mixed logit", "IIA fails and alternatives cluster")],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="ordered_logit", display_name="Ordered Logit", family="linear",
    one_liner="Ordered categories — ratings, Likert, low/med/high.",
    pros=["Respects the ORDER of categories with one slope and a set of cut-points",
          "Coefficients read as proportional odds", "Parsimonious vs multinomial"],
    cons=["Assumes proportional odds (the same slope across all thresholds)",
          "Only ordinal, not the actual distances between categories"],
    limitations=["Proportional-odds violations call for a generalized ordered model"],
    use_when=["Ordinal outcomes: survey scales, credit ratings, severity levels."],
    alternatives=[_a("Ordered probit", "you prefer the latent-normal story"),
                  _a("Multinomial logit", "the categories aren't really ordered")],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="ordered_probit", display_name="Ordered Probit", family="linear",
    one_liner="Ordered categories via a latent score crossing thresholds.",
    pros=["Clean latent-variable interpretation (a normal score crossing cut-points)",
          "Standard in econometrics for ordinal outcomes"],
    cons=["No odds-ratio reading — use marginal effects", "Assumes normal latent errors"],
    limitations=["Same proportional-threshold assumptions as ordered logit"],
    use_when=["Ordinal outcomes where the latent-normal framing fits (survey intensity)."],
    alternatives=[_a("Ordered logit", "you want odds-ratio interpretation")],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="wls", display_name="Weighted Least Squares", family="linear",
    one_liner="OLS that down-weights noisy rows — the fix for heteroskedasticity.",
    pros=["Efficient (correct, tight estimates) under KNOWN heteroskedasticity",
          "Simple extension of OLS"],
    cons=["Needs the weights (the variance structure) — often unknown, so estimated (FGLS)",
          "Wrong weights can hurt more than plain OLS with robust SEs"],
    limitations=["Doesn't fix correlation between errors (that's GLS)"],
    use_when=["Error variance clearly changes with a known quantity (e.g. group size)."],
    alternatives=[_a("OLS with robust SEs", "you just need valid inference, not efficiency"),
                  _a("GLS", "errors are correlated, not just heteroskedastic")],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="gls", display_name="Generalized Least Squares", family="linear",
    one_liner="OLS generalised to correlated / unequal-variance errors.",
    pros=["The general framework: OLS and WLS are special cases",
          "Efficient when the full error covariance is known"],
    cons=["Requires the error covariance matrix — rarely known, must be estimated (FGLS)"],
    limitations=["Misspecified covariance can bias the efficiency gains away"],
    use_when=["Errors are both heteroskedastic AND autocorrelated with a known structure."],
    alternatives=[_a("WLS", "errors are only heteroskedastic, not correlated"),
                  _a("OLS + HAC SEs", "you only need robust inference")],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="robust", display_name="Robust Regression (RLM)", family="linear",
    one_liner="A regression line that shrugs off outliers via Huber weighting.",
    pros=["Resistant to outliers that would drag OLS", "Automatic down-weighting of extremes"],
    cons=["Less efficient than OLS when there are no outliers",
          "Not a fix for the RIGHT model being non-linear"],
    limitations=["Robust to y-outliers; high-leverage x-outliers still need care"],
    use_when=["A few contaminated observations you don't want to hand-delete."],
    alternatives=[_a("OLS", "the data is clean"),
                  _a("Quantile (median) regression", "you want the median line specifically")],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="zip", display_name="Zero-Inflated Poisson", family="linear",
    one_liner="Counts with far more zeros than Poisson expects.",
    pros=["Separates 'structural zeros' (never-events) from ordinary count variation",
          "Fits excess-zero data Poisson/NB can't"],
    cons=["Two linked models to specify and interpret",
          "Needs a rationale for what generates the structural zeros"],
    limitations=["If overdispersion remains in the counts, use zero-inflated NB"],
    use_when=["Count data with a spike at zero: doctor visits, purchases, claims."],
    alternatives=[_a("Poisson", "the zeros are what Poisson already predicts"),
                  _a("Zero-inflated NB", "the non-zero counts are also overdispersed"),
                  _a("Hurdle model", "zeros and positives are two fully separate processes")],
    hyperparameters=[],
))
