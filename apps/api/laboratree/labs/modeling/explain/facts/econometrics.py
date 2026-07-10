"""Curated facts for the econometrics models (5)."""

from __future__ import annotations

from . import Alternative, HyperparameterDoc, ModelFacts, register_facts


def _alt(model: str, when: str) -> Alternative:
    return Alternative(model=model, prefer_when=when)


def _hp(name: str, plain: str, effect: str, rng: str = "") -> HyperparameterDoc:
    return HyperparameterDoc(name=name, plain=plain, effect=effect, typical_range=rng)


register_facts(ModelFacts(
    key="ols", display_name="OLS (with inference)", family="linear",
    one_liner="The regression you can testify about: standard errors, t-stats, CIs.",
    pros=["Every coefficient comes with uncertainty (SE, t, p, CI)",
          "The lingua franca of empirical research", "BLUE under the classical assumptions"],
    cons=["Assumptions (linearity, homoskedasticity, exogeneity) do real work",
          "Association ≠ causation without a design"],
    limitations=["Outliers and collinearity distort estimates; use robust SEs when in doubt"],
    use_when=["The question is 'how big is the effect and can we trust it?' — not raw prediction."],
    alternatives=[
        _alt("Ridge", "prediction is the goal and features are collinear"),
        _alt("XGBoost", "pure prediction with non-linearities"),
        _alt("Poisson GLM", "the outcome is a count"),
    ],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="logit", display_name="Logit", family="linear",
    one_liner="Logistic regression read as odds ratios — the economist's yes/no model.",
    pros=["Odds ratios: 'one more year multiplies the odds by e^β'",
          "Full inference (z, p, CI); marginal effects at meaningful points"],
    cons=["Coefficients aren't effects on probability directly (compute marginal effects)"],
    limitations=["Perfect separation blows up estimates; rare events need corrections"],
    use_when=["Binary outcomes where you must interpret and defend each covariate's role."],
    alternatives=[
        _alt("Probit", "your field's convention, or latent-normal framing fits better"),
        _alt("Logistic regression (ML)", "you only care about prediction accuracy"),
    ],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="probit", display_name="Probit", family="linear",
    one_liner="A hidden score plus normal noise crosses a threshold — 0 or 1.",
    pros=["Natural latent-variable story", "Nearly identical fits to logit; standard in econ/finance"],
    cons=["No odds-ratio reading — interpret via marginal effects only"],
    limitations=["Same separation/rare-event caveats as logit"],
    use_when=["Binary outcomes when your literature reports probits, or the latent-normal story is the model."],
    alternatives=[_alt("Logit", "you want odds ratios and slightly fatter tails")],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="poisson", display_name="Poisson GLM", family="linear",
    one_liner="For counts: a rate that multiplies, never goes negative.",
    pros=["Respects count nature: non-negative, integer-friendly",
          "Coefficients read as rate ratios (e^β)"],
    cons=["Assumes mean = variance — real counts are usually overdispersed"],
    limitations=["Excess zeros need zero-inflated variants"],
    use_when=["Modelling event counts per interval/exposure: claims, visits, defects."],
    alternatives=[
        _alt("Negative binomial", "variance clearly exceeds the mean (overdispersion)"),
        _alt("OLS", "counts are large and behave like continuous values"),
    ],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="quantile", display_name="Quantile Regression", family="linear",
    one_liner="Model the median or any percentile, not the mean — robust and distribution-aware.",
    pros=["Robust to outliers (the median doesn't chase a few extreme points)",
          "Reveals effects that DIFFER across the distribution (the 90th vs the 10th percentile)",
          "No normality assumption on the errors"],
    cons=["Less efficient than OLS when OLS's assumptions actually hold",
          "Each quantile is a separate fit; lines can cross on small samples"],
    limitations=["Interpreting many quantiles at once takes care"],
    use_when=["Skewed outcomes (wages, house prices) or when the tails matter (risk, inequality)."],
    alternatives=[
        _alt("OLS", "the mean is the target and errors are well-behaved"),
        _alt("Robust regression", "you want one robust central line, not the whole distribution"),
    ],
    hyperparameters=[
        _hp("quantile", "Which percentile to fit (0.5 = median).",
            "0.9 models the top; 0.1 the bottom — run several to see effects change.", "0.1–0.9"),
    ],
))

register_facts(ModelFacts(
    key="negative_binomial", display_name="Negative Binomial", family="linear",
    one_liner="Count regression for overdispersed data where Poisson understates the errors.",
    pros=["Handles overdispersion (variance > mean) that Poisson can't",
          "Correct standard errors on real count data", "Coefficients read as rate ratios"],
    cons=["Extra dispersion parameter to estimate", "Still needs a non-negative count outcome"],
    limitations=["Excess zeros want a zero-inflated variant"],
    use_when=["Counts whose variance clearly exceeds the mean — claims, crimes, doctor visits."],
    alternatives=[
        _alt("Poisson", "the count's variance ≈ its mean (no overdispersion)"),
        _alt("Zero-inflated models", "there are far more zeros than any count model expects"),
    ],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="arch", display_name="ARCH", family="timeseries",
    one_liner="Volatility clustering: today's variance rides on recent squared shocks.",
    pros=["Captures volatility clustering — the defining feature of financial returns",
          "Engle's Nobel model; interpretable and the foundation of GARCH"],
    cons=["Needs many lags to match persistence (GARCH does it with far fewer)",
          "Assumes symmetry — a crash and a rally of equal size move variance equally"],
    limitations=["Models variance, not the return level; distribution tails often need Student-t"],
    use_when=["Short-memory volatility, or as the stepping stone to GARCH."],
    alternatives=[
        _alt("GARCH", "volatility is persistent (it almost always is) — far fewer parameters"),
        _alt("EGARCH/GJR", "good and bad news move volatility asymmetrically"),
    ],
    hyperparameters=[
        _hp("p", "How many recent squared shocks feed today's variance.",
            "More lags capture longer shock memory but cost parameters.", "1–3"),
    ],
))

register_facts(ModelFacts(
    key="garch", display_name="GARCH", family="timeseries",
    one_liner="The standard volatility model — turbulence from shocks AND past variance.",
    pros=["Persistent volatility with just two parameters (GARCH(1,1) fits almost everything)",
          "The industry standard for risk (VaR), option pricing, position sizing",
          "α+β measures how long shocks linger (persistence)"],
    cons=["Symmetric by default — leverage effects need EGARCH/GJR",
          "Gaussian errors understate tail risk; use a fat-tailed distribution"],
    limitations=["Models variance only; assumes the process is stationary (α+β<1)"],
    use_when=["Any financial return series where risk forecasting matters."],
    alternatives=[
        _alt("ARCH", "volatility has short memory (rare in finance)"),
        _alt("EGARCH / GJR-GARCH", "downside shocks raise volatility more than upside ones"),
        _alt("Stochastic volatility", "you want volatility to have its own random innovations"),
    ],
    hyperparameters=[
        _hp("p", "ARCH order — recent squared shocks in the variance equation.",
            "Usually 1 is plenty.", "1"),
        _hp("q", "GARCH order — recent variances carried forward.",
            "Usually 1; together (1,1) is the workhorse.", "1"),
    ],
))

register_facts(ModelFacts(
    key="var", display_name="Vector Autoregression (VAR)", family="timeseries",
    one_liner="Several series predict each other from their joint past — impulse responses.",
    pros=["Captures DYNAMIC interdependence between series (GDP, inflation, rates)",
          "Impulse-response functions trace how a shock propagates over time",
          "Granger-causality tests fall right out"],
    cons=["Parameters explode with more series/lags (the curse of dimensionality)",
          "Atheoretical — reduced-form, not structural without extra assumptions"],
    limitations=["Needs stationary series (or a VECM for cointegration)"],
    use_when=["A handful of interrelated macro/financial series you want to model jointly."],
    alternatives=[
        _alt("ARIMA", "you only care about ONE series"),
        _alt("VECM", "the series are non-stationary but cointegrated"),
    ],
    hyperparameters=[
        _hp("lags", "How many past periods of every series feed each equation.",
            "More lags capture longer dynamics but burn degrees of freedom fast.", "1–4"),
    ],
))

register_facts(ModelFacts(
    key="rct", display_name="RCT / A-B Test", family="linear",
    one_liner="Randomisation makes a simple difference in means the causal effect.",
    pros=["The gold standard: random assignment balances ALL confounders, seen and unseen",
          "The estimate is dead simple — a difference in group means",
          "No modelling assumptions needed for unbiasedness"],
    cons=["Often expensive, slow, or unethical to run",
          "External validity: the effect may not transfer beyond the experiment's population"],
    limitations=["Needs genuine randomisation; non-compliance and attrition bite"],
    use_when=["You can actually randomise — feature launches, trials, pricing experiments."],
    alternatives=[
        _alt("Difference-in-Differences", "you can't randomise but have a treated group and pre/post data"),
        _alt("Instrumental Variables", "treatment is self-selected but you have a valid instrument"),
    ],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="did", display_name="Difference-in-Differences", family="linear",
    one_liner="The treated group's before→after change minus the control's.",
    pros=["Removes fixed group differences AND common time trends in one stroke",
          "The workhorse of modern policy evaluation (minimum wage, mergers, rollouts)",
          "Just an OLS with an interaction — transparent and testable"],
    cons=["Rests on the PARALLEL-TRENDS assumption — untestable after treatment",
          "Bad with staggered adoption and heterogeneous effects (use modern estimators)"],
    limitations=["Anticipation effects and concurrent shocks confound it"],
    use_when=["A policy hit some units and not others, and you have before/after data."],
    alternatives=[
        _alt("RCT", "you could randomise instead — cleaner identification"),
        _alt("Synthetic control", "one treated unit and many potential controls"),
    ],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="iv", display_name="Instrumental Variables (2SLS)", family="linear",
    one_liner="An instrument strips endogeneity via two regressions to recover the true effect.",
    pros=["Recovers causal effects when the regressor is endogenous (self-selected, mismeasured)",
          "The two-stage logic is transparent and testable (first-stage F)",
          "Foundational to modern applied econometrics"],
    cons=["A VALID instrument is hard to find and its exclusion restriction is untestable",
          "Weak instruments (first-stage F < 10) give badly biased, imprecise estimates"],
    limitations=["Estimates a LOCAL effect (LATE) for compliers, not everyone"],
    use_when=["Treatment correlates with the error, but you have a relevant, excludable instrument."],
    alternatives=[
        _alt("RCT", "you can randomise — no instrument needed"),
        _alt("Difference-in-Differences", "the endogeneity is a fixed group trait with pre/post data"),
    ],
    hyperparameters=[],
))

register_facts(ModelFacts(
    key="pooled_ols", display_name="Pooled OLS (panel)", family="linear",
    one_liner="Stack every entity-period row and run one regression — the panel baseline.",
    pros=["Simplest panel estimator; uses ALL the variation", "Efficient when entities really are exchangeable"],
    cons=["Ignores that rows from the same entity are related (SEs too small — cluster them)",
          "Entity-level confounders bias the coefficients"],
    limitations=["Rarely defensible causally without further structure"],
    use_when=["As the baseline every panel paper reports first, before FE/RE."],
    alternatives=[
        _alt("Fixed effects", "entity-level confounders are plausible (they usually are)"),
        _alt("Random effects", "entity effects are credibly uncorrelated with the regressors"),
    ],
    hyperparameters=[
        _hp("entity_column", "Which column identifies the repeated entity (person/firm/country).",
            "Wrong entity id = wrong clustering and wrong panel story.", ""),
    ],
))

register_facts(ModelFacts(
    key="fixed_effects", display_name="Fixed Effects (within)", family="linear",
    one_liner="Demean within each entity — time-constant confounders vanish.",
    pros=["Kills ALL time-constant confounders without measuring them — the causal workhorse",
          "Each entity serves as its own control"],
    cons=["Throws away between-entity variation (only WITHIN changes identify the effect)",
          "Can't estimate effects of time-constant variables (they're demeaned away)"],
    limitations=["Time-VARYING confounders still bias it; noisy with short panels"],
    use_when=["Repeated observations per entity and worry about 'some firms/people just differ'."],
    alternatives=[
        _alt("Random effects", "a Hausman test can't tell FE and RE apart — RE is more efficient"),
        _alt("Pooled OLS", "entity effects are demonstrably negligible"),
    ],
    hyperparameters=[
        _hp("entity_column", "The repeated-entity id whose means are subtracted.",
            "The whole estimator is defined by this grouping.", ""),
    ],
))

register_facts(ModelFacts(
    key="random_effects", display_name="Random Effects", family="linear",
    one_liner="Entity intercepts as draws from a distribution — efficient when exogenous.",
    pros=["More efficient than FE (uses within AND between variation)",
          "Can estimate time-constant covariates, unlike FE"],
    cons=["Requires entity effects UNCORRELATED with regressors — a strong assumption",
          "When that fails, coefficients are biased (run the Hausman test)"],
    limitations=["Assumption rarely holds in observational economics — FE is the safer default"],
    use_when=["Entities look like random draws (survey panels) and efficiency matters."],
    alternatives=[
        _alt("Fixed effects", "the Hausman test rejects — effects correlate with X"),
        _alt("Pooled OLS", "the estimated entity variance is ~zero"),
    ],
    hyperparameters=[
        _hp("entity_column", "The grouping whose intercepts are treated as random draws.",
            "Defines the variance decomposition.", ""),
    ],
))

register_facts(ModelFacts(
    key="arima", display_name="ARIMA", family="timeseries",
    one_liner="Autoregression + differencing + moving average on one series.",
    pros=["Principled intervals; orders diagnosed from ACF/PACF", "Great on short, well-behaved series"],
    cons=["No seasonality (that's SARIMA) or exogenous drivers (ARIMAX)"],
    limitations=["Linear dynamics; regime changes break it"],
    use_when=["A non-seasonal series where the recent past clearly drives the near future."],
    alternatives=[
        _alt("SARIMA", "the series has a seasonal rhythm"),
        _alt("ETS", "you want a robust forecast without order-picking"),
    ],
    hyperparameters=[
        _hp("order", "The (p, d, q) triple: AR lags, differences, MA lags.",
            "Diagnose from ACF/PACF; small orders almost always suffice.", "(1,1,1)"),
    ],
))
