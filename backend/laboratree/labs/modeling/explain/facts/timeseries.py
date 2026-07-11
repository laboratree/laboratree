"""Curated facts for the time-series models (2)."""

from __future__ import annotations

from . import Alternative, HyperparameterDoc, ModelFacts, register_facts


def _alt(model: str, when: str) -> Alternative:
    return Alternative(model=model, prefer_when=when)


def _hp(name: str, plain: str, effect: str, rng: str = "") -> HyperparameterDoc:
    return HyperparameterDoc(name=name, plain=plain, effect=effect, typical_range=rng)


register_facts(ModelFacts(
    key="ets", display_name="Exponential Smoothing (ETS)", family="timeseries",
    one_liner="Level + trend + season, each updated with fading memory.",
    pros=["Fast, robust, hard to break — the forecasting workhorse",
          "Handles trend and seasonality explicitly", "Very explainable components"],
    cons=["No exogenous variables (can't use other columns)",
          "Prediction intervals are optimistic under structural change"],
    limitations=["One series at a time; assumes patterns persist"],
    use_when=["Any single seasonal/trending series — the baseline to beat in forecasting."],
    alternatives=[
        _alt("SARIMA", "autocorrelation structure matters or you need better intervals"),
        _alt("LSTM", "many related series and non-linear dynamics with lots of history"),
    ],
    hyperparameters=[
        _hp("trend", "Additive/none — is there a persistent drift?",
            "Add it when the series climbs or sinks steadily.", "add/none"),
        _hp("seasonal", "Additive/none — a repeating cycle?",
            "Add for weekly/monthly rhythms.", "add/none"),
        _hp("seasonal_periods", "Length of the cycle (12 = monthly-in-a-year).",
            "Must match the real rhythm or the season component learns garbage.", "4/7/12/52"),
    ],
))

register_facts(ModelFacts(
    key="sarima", display_name="SARIMA", family="timeseries",
    one_liner="Difference to stationary, then lags and past errors forecast the future.",
    pros=["Statistically principled with honest prediction intervals",
          "Interpretable orders (p,d,q) diagnosed from ACF/PACF", "Small-data friendly"],
    cons=["Requires stationarity work and order-picking skill",
          "Linear dynamics only; one series at a time"],
    limitations=["Long seasonal periods get expensive; regime changes break it"],
    use_when=["A well-behaved series where you must defend the intervals (finance, ops planning)."],
    alternatives=[
        _alt("ETS", "you want a strong forecast without order-picking"),
        _alt("LSTM", "non-linear dynamics and plenty of data"),
    ],
    hyperparameters=[
        _hp("p", "AR order — how many past VALUES feed today.", "Read from the PACF cutoff.", "0–3"),
        _hp("d", "Differencing — how many times to subtract the previous value.",
            "Raise until the series looks stationary.", "0–2"),
        _hp("q", "MA order — how many past ERRORS feed today.", "Read from the ACF cutoff.", "0–3"),
        _hp("s", "The seasonal period.", "12 for monthly-yearly, 7 for daily-weekly.", "4/7/12"),
    ],
))
