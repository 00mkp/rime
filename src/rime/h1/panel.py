"""Zero-filled monthly count panels for the locked H1 models (prereg/hypotheses.md)."""
import pandas as pd

SOUTHERN_TIER = frozenset({"southeast", "south", "southwest", "west"})
NORTHERN_TIER = frozenset({"northwest", "northern_rockies_plains", "upper_midwest", "ohio_valley"})
WINTER = (11, 12, 1, 2, 3)
OUTCOMES = ("wx", "non_wx", "fatal_wx")


def phase_lookup(enso: pd.DataFrame, lag: int = 0, super_level: bool = False) -> pd.DataFrame:
    """Phase for each month = ENSO phase `lag` months earlier."""
    e = enso.sort_values("month").reset_index(drop=True)
    phase = e["phase"].where(~(super_level & e["super"] & (e["phase"] == "el_nino")), "super_el_nino")
    shifted = pd.DataFrame({"month": e["month"] + pd.DateOffset(months=lag), "phase": phase})
    return pd.DataFrame({"year": shifted["month"].dt.year, "month": shifted["month"].dt.month,
                         "phase": shifted["phase"].to_numpy()})


def _select(events: pd.DataFrame, category: str, outcome: str, regions) -> pd.DataFrame:
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}")
    e = events[(events["ev_type"] == "ACC") & (events["category"] == category)]
    if regions is not None:
        e = e[e["region"].isin(regions)]
    if outcome == "wx":
        return e[e["wx_involved"]]
    if outcome == "non_wx":
        return e[~e["wx_involved"]]
    return e[e["wx_involved"] & e["fatal"]]


def _grid(years, phases: pd.DataFrame) -> pd.DataFrame:
    g = pd.DataFrame([(y, m) for y in sorted(years) for m in range(1, 13)], columns=["year", "month"])
    out = g.merge(phases, on=["year", "month"], how="left")
    if out["phase"].isna().any():
        raise ValueError("ENSO phase missing for some study months")
    return out


def _counts(e: pd.DataFrame, name: str) -> pd.DataFrame:
    return e.groupby(["year", "month"]).size().rename(name).reset_index()


def monthly_panel(events, phases, *, category: str, years: list[int], outcome: str = "wx",
                  regions: frozenset[str] | None = None) -> pd.DataFrame:
    c = _counts(_select(events, category, outcome, regions), "count")
    out = _grid(years, phases).merge(c, on=["year", "month"], how="left")
    out["count"] = out["count"].fillna(0).astype(int)
    return out[["year", "month", "phase", "count"]]


def tier_panel(events, phases, *, category: str, years: list[int], tier: frozenset[str],
               outcome: str = "wx") -> pd.DataFrame:
    tier_c = _counts(_select(events, category, outcome, tier), "tier_count")
    all_c = _counts(_select(events, category, outcome, None), "total")
    out = (_grid(years, phases).merge(tier_c, on=["year", "month"], how="left")
           .merge(all_c, on=["year", "month"], how="left").fillna({"tier_count": 0, "total": 0}))
    out = out[out["month"].isin(WINTER)].copy()
    out["tier_count"] = out["tier_count"].astype(int)
    out["rest_count"] = (out["total"] - out["tier_count"]).astype(int)
    out["season"] = out["year"].where(out["month"] >= 11, out["year"] - 1)
    return out[["year", "month", "season", "phase", "tier_count", "rest_count"]].reset_index(drop=True)
