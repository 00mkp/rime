"""`rime h2`: locked H2a/H2b/H3a/H3b tests once ERA5 annual indices exist."""
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from rime import paths
from rime.cli import register
from rime.exposure import load_exposure
from rime.h1.models import Effect, holm
from rime.h1.run import require_prereg_lock
from rime.h2.models import link_test, trend_test
from rime.ntsb.classify import CATEGORIES
from rime.power import study_years

HAZARD_INDEX = {"icing": "icing", "turbulence": "turbulence", "convective": "convective"}
INDEX_YEARS = range(1990, 2025)
H2B_MIN, H3B_MIN = 30, 20
H3_CATEGORIES = ("airliner", "charter", "ga_turbine")
H3B_YEARS = range(2004, 2025)


def _row(family, test, e: Effect | None, *, category="", hazard="", n=0, status=None) -> dict:
    if e is None:
        return {"family": family, "test": test, "category": category, "hazard": hazard, "estimate": np.nan,
                "ci_lo": np.nan, "ci_hi": np.nan, "p": np.nan, "n": n, "status": status, "model": ""}
    return {"family": family, "test": test, "category": category, "hazard": hazard, "estimate": e.rr,
            "ci_lo": e.ci_lo, "ci_hi": e.ci_hi, "p": e.p, "n": e.n_events, "status": e.status, "model": e.model}


def _holm_family(rows: list[dict]) -> list[dict]:
    tested = {i: Effect(0, 0, 0, r["p"], 0, "ok") for i, r in enumerate(rows) if r["status"] in ("ok", "not_estimable")}
    adj = holm(tested) if tested else {}
    for i, r in enumerate(rows):
        r["p_holm"], r["reject"] = adj.get(i, (np.nan, None))
    return rows


def build_h2_rows(hazard_counts: pd.DataFrame, annual: pd.DataFrame, exposure: pd.DataFrame,
                  breaks: dict[str, bool], *, force_break: bool = False) -> pd.DataFrame:
    """Confirmatory rows. force_break=True gives prereg §5.2 (post-2008 indicator in H2b/H3b)."""
    a = annual[annual["complete"] & annual["year"].isin(INDEX_YEARS)].set_index("year")
    out = []
    # H2a: two-sided trends of the three hazard indices, 1990–2024
    fam = [_row("H2a", f"{h} index trend", trend_test(a.index, a[col]), hazard=h)
           for h, col in HAZARD_INDEX.items()]
    out += _holm_family(fam)
    # H2b: one-sided index→accident links per hazard × category, primary periods
    fam = []
    for h, col in HAZARD_INDEX.items():
        for c in CATEGORIES:
            exp_c = exposure[exposure["category"] == c].set_index("year")["flight_hours"]
            hc = hazard_counts[(hazard_counts["hazard"] == h) & (hazard_counts["category"] == c)].set_index("year")["count"]
            years = [y for y in study_years(c, exp_c.index, hc.index) if y in a.index]
            counts = hc.reindex(years).fillna(0)
            n = int(counts.sum())
            if n < H2B_MIN:
                fam.append(_row("H2b", f"{h} → {c}", None, category=c, hazard=h, n=n, status="descriptive"))
            else:
                e = link_test(counts, a.loc[years, col], exp_c.loc[years],
                              break_2008=force_break or breaks.get(h, False))
                fam.append(_row("H2b", f"{h} → {c}", e, category=c, hazard=h))
    out += _holm_family(fam)
    # H3a: one-sided positive trend of the HIWC index
    out += _holm_family([_row("H3a", "hiwc index trend", trend_test(a.index, a["hiwc"], one_sided=True), hazard="hiwc")])
    # H3b: turbine categories combined, en-route hazard accidents vs HIWC index, 2004–2024
    hrs = exposure[exposure["category"].isin(H3_CATEGORIES)].pivot(index="year", columns="category", values="flight_hours")
    hrs = hrs.dropna().sum(axis=1)
    h3 = hazard_counts[(hazard_counts["hazard"] == "h3") & hazard_counts["category"].isin(H3_CATEGORIES)]
    h3 = h3.groupby("year")["count"].sum()
    years = [y for y in H3B_YEARS if y in hrs.index and y in a.index]
    counts = h3.reindex(years).fillna(0)
    n = int(counts.sum())
    if n < H3B_MIN:
        fam = [_row("H3b", "hiwc → turbine en-route hazard accidents", None, category="turbine", hazard="h3",
                    n=n, status="descriptive")]
    else:
        fam = [_row("H3b", "hiwc → turbine en-route hazard accidents",
                    link_test(counts, a.loc[years, "hiwc"], hrs.loc[years], break_2008=force_break),
                    category="turbine", hazard="h3")]
    out += _holm_family(fam)
    return pd.DataFrame(out)


def build_h2_sensitivity(hazard_counts, annual, exposure, breaks) -> pd.DataFrame:
    rows = build_h2_rows(hazard_counts, annual, exposure, breaks, force_break=True)
    rows = rows[rows["family"].isin(["H2b", "H3b"])].drop(columns=["p_holm", "reject"])
    return rows.assign(sensitivity="post2008_indicator")


def run_h2() -> None:
    sha = require_prereg_lock()
    p = paths.PROCESSED / "era5_annual.parquet"
    if not p.exists():
        print("  ERA5 indices missing: run `rime era5` after setting up a Copernicus CDS account.")
        return
    annual = pd.read_parquet(p)
    missing = [y for y in INDEX_YEARS if y not in set(annual.loc[annual["complete"], "year"])]
    if missing:
        print(f"  ERA5 indices missing or incomplete for {len(missing)} years "
              f"({missing[0]}…{missing[-1]}); `rime era5` resumes the download.")
        return
    breaks_df = pd.read_csv(paths.RESULTS / "qa" / "hazard_break.csv")
    breaks = dict(zip(breaks_df["hazard"], breaks_df["post2008_indicator"].astype(bool)))
    inputs = (pd.read_parquet(paths.PROCESSED / "hazard_counts.parquet"), annual, load_exposure(), breaks)
    rows = build_h2_rows(*inputs)
    out = paths.RESULTS / "h2"
    out.mkdir(parents=True, exist_ok=True)
    rows.to_csv(out / "confirmatory.csv", index=False)
    build_h2_sensitivity(*inputs).to_csv(out / "sensitivity.csv", index=False)
    (out / "meta.json").write_text(json.dumps({
        "prereg_sha": sha, "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "breaks": breaks}, indent=2))
    print(rows[["family", "test", "estimate", "ci_lo", "ci_hi", "p_holm", "reject", "n", "status"]].to_string(index=False))


register("h2", run_h2, "run the locked H2/H3 hazard tests (requires prereg-v1 and ERA5 indices)")
