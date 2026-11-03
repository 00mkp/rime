"""Locked H1 models (prereg/hypotheses.md §2–3) and Holm correction."""
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests

PHASE = "C(phase, Treatment('neutral'))"
LEVELS = ("el_nino", "la_nina", "super_el_nino")


@dataclass
class Effect:
    rr: float
    ci_lo: float
    ci_hi: float
    p: float
    n_events: int
    status: str  # "ok" | "not_estimable"
    model: str = "nb"  # "nb" | "poisson_boundary" (NB ML at alpha -> 0) | "binomial" | "none"


def _not_estimable(n: int) -> Effect:
    return Effect(np.nan, np.nan, np.nan, 1.0, n, "not_estimable", "none")


def _effect(params, bse, name: str, n: int, one_sided: bool = False) -> Effect:
    b, se = params[name], bse[name]
    if not (np.isfinite(b) and np.isfinite(se) and se > 0):
        return _not_estimable(n)
    z = b / se
    p = stats.norm.sf(z) if one_sided else 2 * stats.norm.sf(abs(z))
    return Effect(float(np.exp(b)), float(np.exp(b - 1.96 * se)), float(np.exp(b + 1.96 * se)),
                  float(p), n, "ok")


def _levels(panel: pd.DataFrame) -> list[str]:
    return [lv for lv in LEVELS if lv in set(panel["phase"])]


FE = f"count ~ {PHASE} + C(year) + C(month)"


def _fit_nb(panel: pd.DataFrame):
    """Discrete NB2 with year and month fixed effects; first converging optimizer wins.

    When NB fails because the data show no overdispersion, the ML solution is on the
    boundary alpha -> 0, i.e. the Poisson model; that fit is returned with
    `rime_model = "poisson_boundary"`. Otherwise None.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pois = smf.glm(FE, panel, family=sm.families.Poisson()).fit()
        start = np.append(pois.params.to_numpy(), 0.05)
        alphas = []
        for method in ("newton", "bfgs", "lbfgs", "nm"):
            try:
                res = smf.negativebinomial(FE, panel).fit(start_params=start, method=method,
                                                         maxiter=2000, disp=0)
            except (np.linalg.LinAlgError, ValueError):
                continue
            if res.mle_retvals.get("converged", False) and np.all(np.isfinite(res.bse)):
                res.rime_model = "nb"
                return res
            if np.isfinite(res.params["alpha"]):
                alphas.append(float(res.params["alpha"]))
    if alphas and min(alphas) < 1e-4 and np.all(np.isfinite(pois.bse)):
        pois.rime_model = "poisson_boundary"
        return pois
    return None


def fit_h1n(panel: pd.DataFrame) -> dict[str, Effect]:
    n = int(panel["count"].sum())
    levels = _levels(panel)
    res = _fit_nb(panel) if n > 0 else None
    if res is None:
        return {lv: _not_estimable(n) for lv in levels}
    return {lv: _with_model(_effect(res.params, res.bse, f"{PHASE}[T.{lv}]", n), res.rime_model)
            for lv in levels}


def _with_model(e: Effect, model: str) -> Effect:
    e.model = model if e.status == "ok" else e.model
    return e


def _alpha(res) -> float:
    return float(res.params["alpha"]) if res.rime_model == "nb" else 1e-8


def fit_h1n_original(panel: pd.DataFrame, hours: pd.Series) -> dict[str, Effect]:
    """Sensitivity 8: NB GLM, month FE + quadratic year trend, log(hours/12) offset, SEs clustered by year."""
    n = int(panel["count"].sum())
    levels = _levels(panel)
    nb = _fit_nb(panel) if n > 0 else None
    if nb is None:
        return {lv: _not_estimable(n) for lv in levels}
    d = panel.assign(yc=panel["year"] - panel["year"].mean())
    offset = np.log(d["year"].map(hours).astype(float) / 12)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = smf.glm(f"count ~ {PHASE} + C(month) + yc + I(yc**2)", d, offset=offset,
                      family=sm.families.NegativeBinomial(alpha=_alpha(nb))
                      ).fit(cov_type="cluster", cov_kwds={"groups": d["year"]})
    return {lv: _effect(res.params, res.bse, f"{PHASE}[T.{lv}]", n) for lv in levels}


def fit_h1r(tier: pd.DataFrame, target: str) -> Effect:
    """Binomial GLM of tier share on phase; one-sided test that the target phase raises the share."""
    d = tier[(tier["tier_count"] + tier["rest_count"]) > 0]
    n = int(d["tier_count"].sum() + d["rest_count"].sum())
    if target not in set(d["phase"]) or n == 0:
        return _not_estimable(n)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = smf.glm(f"tier_count + rest_count ~ {PHASE}", d, family=sm.families.Binomial()).fit()
    return _with_model(_effect(res.params, res.bse, f"{PHASE}[T.{target}]", n, one_sided=True), "binomial")


def holm(effects: dict[str, Effect]) -> dict[str, tuple[float, bool]]:
    keys = list(effects)
    reject, p_adj, _, _ = multipletests([effects[k].p for k in keys], alpha=0.05, method="holm")
    return {k: (float(p), bool(r)) for k, p, r in zip(keys, p_adj, reject)}
