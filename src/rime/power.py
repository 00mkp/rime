"""Power analysis: smallest ENSO rate ratio detectable per aircraft category.

Uses only annual weather-involved counts per category (allowed pre-prereg) and the
historical ENSO phase sequence as the covariate. No outcome is split by phase.
"""
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

from rime import paths
from rime.cli import register

SEED = 20261102
RR_GRID = np.round(np.arange(1.05, 2.0001, 0.05), 2)
TARGET_POWER = 0.80
ALPHA = 0.05 / 10  # 5 categories x 2 phases
N_SIMS = 500
END_YEAR = 2024  # 2025+ still being entered by NTSB (see results/qa/data_quality.md)
FIRST_YEAR = 1990


def monthly_dispersion(years, counts) -> float:
    """NB2 alpha for monthly counts, from detrended annual counts (method of moments)."""
    years, counts = np.asarray(years, float), np.asarray(counts, float)
    fit = np.polyval(np.polyfit(years, counts, 1), years)
    var = np.sum((counts - fit) ** 2) / max(len(counts) - 2, 1)
    mean = fit.mean()
    if mean <= 0:
        return 1e-3
    return max(12 * (var - mean) / mean**2, 1e-3)


def _design(phases: pd.Series) -> np.ndarray:
    n = len(phases)
    trend = (np.arange(n) - n / 2) / n
    return np.column_stack([np.ones(n), trend,
                            (phases == "el_nino").to_numpy(float),
                            (phases == "la_nina").to_numpy(float)])


def simulate_power(monthly_mean: float, dispersion: float, phases: pd.Series, rate_ratio: float,
                   alpha: float, n_sims: int, rng: np.random.Generator,
                   *, target: str = "el_nino") -> float:
    phases = pd.Series(phases).reset_index(drop=True)
    X = _design(phases)
    col = 2 if target == "el_nino" else 3
    mu = monthly_mean * np.where(phases == target, rate_ratio, 1.0)
    size = 1.0 / dispersion
    family = sm.families.NegativeBinomial(alpha=dispersion)
    hits = 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for _ in range(n_sims):
            y = rng.negative_binomial(size, size / (size + mu))
            if y.sum() == 0:
                continue
            try:
                res = sm.GLM(y, X, family=family).fit()
            except (ValueError, np.linalg.LinAlgError):
                continue
            if res.pvalues[col] < alpha and res.params[col] > 0:
                hits += 1
    return hits / n_sims


def minimal_detectable_rr(monthly_mean: float, dispersion: float, phases: pd.Series,
                          alpha: float, n_sims: int, rng: np.random.Generator,
                          *, target: str = "el_nino") -> float | None:
    """Smallest RR on RR_GRID with power ≥ 0.80 (power is monotone in RR → bisection)."""
    power = lambda rr: simulate_power(monthly_mean, dispersion, phases, rr, alpha, n_sims, rng, target=target)
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
        years = sorted(set(exposure.loc[exposure.category == cat, "year"])
                       & set(c["year"]) & set(range(FIRST_YEAR, END_YEAR + 1)))
        c = c.set_index("year").loc[years]
        months = enso[enso["month"].dt.year.isin(years)].sort_values("month")
        mm = c["wx_accidents"].mean() / 12
        disp = monthly_dispersion(years, c["wx_accidents"])
        row = {"category": cat, "years": f"{years[0]}-{years[-1]} ({len(years)} yrs)",
               "total_wx_accidents": int(c["wx_accidents"].sum()),
               "monthly_mean": round(mm, 3), "dispersion": round(disp, 4)}
        for target in ("el_nino", "la_nina"):
            row[f"mdrr_{target}"] = minimal_detectable_rr(mm, disp, months["phase"], ALPHA, N_SIMS, rng, target=target)
        rows.append(row)
        print(f"  {row}")
    out = paths.RESULTS / "power"
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out / "mdrr.csv", index=False)


register("power", run_power, "power analysis: minimal detectable ENSO rate ratios")
