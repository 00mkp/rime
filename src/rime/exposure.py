"""Annual flight-hour exposure by aircraft category (hand-curated, see data/manual/EXPOSURE_SOURCES.md)."""
from pathlib import Path

import pandas as pd

from rime import paths
from rime.ntsb.classify import CATEGORIES

COLUMNS = ["year", "category", "flight_hours", "departures", "source", "source_url"]


def load_exposure(path: Path | None = None) -> pd.DataFrame:
    df = pd.read_csv(path or paths.MANUAL / "exposure_annual.csv", comment="#")
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"exposure table missing columns: {sorted(missing)}")
    df = df[COLUMNS].astype({"year": int, "flight_hours": float, "departures": float})
    bad = set(df["category"]) - set(CATEGORIES)
    if bad:
        raise ValueError(f"unknown category in exposure table: {sorted(bad)}")
    if (df["flight_hours"] <= 0).any() or df["flight_hours"].isna().any():
        raise ValueError("flight_hours must be positive")
    dup = df.duplicated(["year", "category"])
    if dup.any():
        raise ValueError(f"duplicate (year, category): {df.loc[dup, ['year', 'category']].values.tolist()}")
    return df.reset_index(drop=True)


def rate_frame(counts: pd.DataFrame, exposure: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Join counts to exposure; category-years without exposure are returned separately, never zeroed."""
    m = counts.merge(exposure[["year", "category", "flight_hours", "departures"]],
                     on=["year", "category"], how="left", indicator=True)
    has = m["_merge"] == "both"
    joined = m[has].drop(columns="_merge").reset_index(drop=True)
    dropped = m.loc[~has, ["year", "category"]].reset_index(drop=True)
    return joined, dropped
