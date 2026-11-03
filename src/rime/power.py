"""Power analysis: smallest ENSO rate ratio detectable per aircraft category.

Uses only annual weather-involved counts per category (allowed pre-prereg) and the
historical ENSO phase sequence as the covariate. No outcome is split by phase.
"""
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from rime import paths
from rime.cli import register

SEED = 20261102
RR_GRID = np.round(np.arange(1.05, 2.0001, 0.05), 2)
TARGET_POWER = 0.80
ALPHA = 0.05 / 10  # 5 categories x 2 phases
N_SIMS = 500
END_YEAR = 2024  # 2025+ still being entered by NTSB (see results/qa/data_quality.md)
# Primary periods start after exposure-definition breaks (data/manual/EXPOSURE_SOURCES.md):
# March 1997 commuter rule moved 10+ seat scheduled ops from Part 135 to 121;
# FAA redesigned the GA/Part 135 survey in 2004.
PRIMARY_START = {"airliner": 1997, "charter": 2004, "ga_piston": 2004,
                 "ga_turbine": 2004, "helicopter": 2004}


def study_years(category: str, exposure_years, count_years) -> list[int]:
    lo = PRIMARY_START[category]
    return sorted(y for y in set(exposure_years) & set(count_years) if lo <= y <= END_YEAR)


def monthly_dispersion(years, counts) -> float:
    """NB2 alpha for monthly counts, from detrended annual counts (method of moments)."""
    years, counts = np.asarray(years, float), np.asarray(counts, float)
    fit = np.polyval(np.polyfit(years, counts, 1), years)
    var = np.sum((counts - fit) ** 2) / max(len(counts) - 2, 1)
    mean = fit.mean()
    if mean <= 0:
        return 1e-3
    return max(12 * (var - mean) / mean**2, 1e-3)


def annual_dispersion(years, counts) -> float:
    """Year-level gamma variance: extra-Poisson variance of detrended annual counts / mean²."""
    return max(monthly_dispersion(years, counts) / 12, 1e-4)


def _design(phases: pd.Series, gidx: np.ndarray) -> np.ndarray:
    """El Niño and La Niña indicators (neutral = reference) plus one fixed effect per group."""
    return np.column_stack([(phases == "el_nino").to_numpy(float),
                            (phases == "la_nina").to_numpy(float),
                            np.eye(gidx.max() + 1)[gidx]])


def simulate_power(monthly_mean: float, dispersion: float, phases: pd.Series, rate_ratio: float,
                   alpha: float, n_sims: int, rng: np.random.Generator,
                   *, target: str = "el_nino", year_dispersion: float = 0.0,
                   groups: np.ndarray | None = None) -> float:
    """Share of simulations where the target phase is significantly *higher* than neutral.

    Simulated months share a gamma year effect (variance `year_dispersion`) within each
    group (default: consecutive 12-month blocks), plus NB2 month noise (`dispersion`, 0 =
    Poisson). Inference mirrors the prereg design: group (year) fixed effects absorb any
    shock shared by a year's months, including errors in annual exposure; Poisson GLM with
    model-based SEs; two-sided p-value plus a sign condition. Month-of-year effects are not
    simulated (flat seasonality), a stated simplification.
    """
    phases = pd.Series(phases).reset_index(drop=True)
    n = len(phases)
    groups = np.arange(n) // 12 if groups is None else np.asarray(groups)
    _, gidx = np.unique(groups, return_inverse=True)
    n_groups = gidx.max() + 1
    X = _design(phases, gidx)
    col = 0 if target == "el_nino" else 1
    base = monthly_mean * np.where(phases == target, rate_ratio, 1.0)
    hits = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for _ in range(n_sims):
            if year_dispersion > 0:
                shape = 1.0 / year_dispersion
                mu = base * rng.gamma(shape, 1.0 / shape, n_groups)[gidx]
            else:
                mu = base
            if dispersion > 0:
                size = 1.0 / dispersion
                y = rng.negative_binomial(size, size / (size + mu))
            else:
                y = rng.poisson(mu)
            if y.sum() == 0:
                continue
            try:
                res = sm.GLM(y, X, family=sm.families.Poisson()).fit()
            except (ValueError, np.linalg.LinAlgError):
                continue
            p = 2 * stats.norm.sf(abs(res.params[col] / res.bse[col]))
            if p < alpha and res.params[col] > 0:
                hits += 1
    return hits / n_sims


def simulate_share_power(monthly_total: float, share: float, phases: pd.Series, rate_ratio: float,
                         alpha: float, n_sims: int, rng: np.random.Generator,
                         *, target: str = "el_nino", year_dispersion: float = 0.0,
                         groups: np.ndarray | None = None) -> float:
    """H1-R design: does the region tier's share of weather accidents rise in `target` months?

    Tier and rest-of-country counts share each group's (season's) gamma shock, so national
    shocks and exposure errors cancel. Inference: binomial GLM of tier vs rest counts per
    month on phase indicators; two-sided p plus a sign condition.
    """
    phases = pd.Series(phases).reset_index(drop=True)
    n = len(phases)
    groups = np.arange(n) // 12 if groups is None else np.asarray(groups)
    _, gidx = np.unique(groups, return_inverse=True)
    X = np.column_stack([np.ones(n), (phases == "el_nino").to_numpy(float),
                         (phases == "la_nina").to_numpy(float)])
    col = 1 if target == "el_nino" else 2
    tier_mu = monthly_total * share * np.where(phases == target, rate_ratio, 1.0)
    rest_mu = np.full(n, monthly_total * (1 - share))
    hits = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for _ in range(n_sims):
            g = (rng.gamma(1 / year_dispersion, year_dispersion, gidx.max() + 1)[gidx]
                 if year_dispersion > 0 else 1.0)
            tier, rest = rng.poisson(tier_mu * g), rng.poisson(rest_mu * g)
            keep = (tier + rest) > 0
            if keep.sum() < 10:
                continue
            try:
                res = sm.GLM(np.column_stack([tier, rest])[keep], X[keep],
                             family=sm.families.Binomial()).fit()
            except (ValueError, np.linalg.LinAlgError):
                continue
            p = 2 * stats.norm.sf(abs(res.params[col] / res.bse[col]))
            if p < alpha and res.params[col] > 0:
                hits += 1
    return hits / n_sims


def minimal_detectable_rr(monthly_mean: float, dispersion: float, phases: pd.Series,
                          alpha: float, n_sims: int, rng: np.random.Generator,
                          *, target: str = "el_nino", year_dispersion: float = 0.0,
                          groups: np.ndarray | None = None,
                          share: float | None = None) -> float | None:
    """Smallest RR on RR_GRID with power ≥ 0.80 (power is monotone in RR → bisection).

    With `share`, uses the H1-R tier-share design (monthly_mean = national monthly total).
    """
    if share is None:
        power = lambda rr: simulate_power(monthly_mean, dispersion, phases, rr, alpha, n_sims, rng,
                                          target=target, year_dispersion=year_dispersion, groups=groups)
    else:
        power = lambda rr: simulate_share_power(monthly_mean, share, phases, rr, alpha, n_sims, rng,
                                                target=target, year_dispersion=year_dispersion, groups=groups)
    if power(RR_GRID[-1]) < TARGET_POWER:
        return None
    lo, hi = -1, len(RR_GRID) - 1  # invariant: power(grid[hi]) ≥ target
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if power(RR_GRID[mid]) >= TARGET_POWER:
            hi = mid
        else:
            lo = mid
    return float(RR_GRID[hi])


H1R_SHARES = (0.40, 0.20)  # assumed tier shares of national winter weather events; NOT computed
# from outcomes. The southern/northern tiers each hold 4 of 9 CONUS regions; 0.40 is a typical
# share, 0.20 a pessimistic one.
H1R_ALPHA = 0.05  # two-sided-with-sign at 0.05 == one-sided 0.025 (Holm, 2 tests)


def _h1r_rows(nat: dict, months: pd.DataFrame, mm: float, ydisp: float, rng) -> list[dict]:
    """H1-R power for ga_piston: winter (Nov–Mar) months, tier-share design, assumed tier shares."""
    w = months[months["month"].dt.month.isin([11, 12, 1, 2, 3])]
    season = np.where(w["month"].dt.month >= 11, w["month"].dt.year, w["month"].dt.year - 1)
    rows = []
    for share in H1R_SHARES:
        row = {**nat, "family": "H1-R (winter, tier share)", "share": share}
        for target in ("el_nino", "la_nina"):
            row[f"mdrr_{target}"] = minimal_detectable_rr(
                mm, 0.0, w["phase"], H1R_ALPHA, N_SIMS, rng,
                target=target, year_dispersion=ydisp, groups=season, share=share)
        rows.append(row)
        print(f"  {row}")
    return rows


def run_power() -> None:
    from rime.exposure import load_exposure
    from rime.ntsb.events import counts_by_category_year

    events = pd.read_parquet(paths.PROCESSED / "events_aircraft.parquet")
    counts = counts_by_category_year(events)
    enso = pd.read_parquet(paths.PROCESSED / "enso_monthly.parquet")
    exposure = load_exposure()
    rng = np.random.default_rng(SEED)
    rows = []
    for cat, c in counts.groupby("category"):
        years = study_years(cat, exposure.loc[exposure.category == cat, "year"], c["year"])
        c = c.set_index("year").loc[years]
        months = enso[enso["month"].dt.year.isin(years)].sort_values("month")
        mm = c["wx_accidents"].mean() / 12
        ydisp = annual_dispersion(years, c["wx_accidents"])
        groups = months["month"].dt.year.to_numpy()
        row = {"family": "H1-N", "category": cat, "share": 1.0,
               "years": f"{years[0]}-{years[-1]} ({len(years)} yrs)",
               "total_wx_accidents": int(c["wx_accidents"].sum()),
               "monthly_mean": round(mm, 3), "year_dispersion": round(ydisp, 4)}
        for target in ("el_nino", "la_nina"):
            row[f"mdrr_{target}"] = minimal_detectable_rr(
                mm, 0.0, months["phase"], ALPHA, N_SIMS, rng,
                target=target, year_dispersion=ydisp, groups=groups)
        rows.append(row)
        print(f"  {row}")
        if cat == "ga_piston":
            rows += _h1r_rows(row, months, mm, ydisp, rng)
    out = paths.RESULTS / "power"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "mdrr.csv", index=False)


register("power", run_power, "power analysis: minimal detectable ENSO rate ratios")
