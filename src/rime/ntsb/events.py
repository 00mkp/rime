"""One row per in-scope aircraft involvement in a US accident/incident, 1990 onward.

ENSO is deliberately NOT joined here: before the prereg-v1 tag the only outcome
summary allowed is counts per category per year.
"""
import pandas as pd

from rime import paths
from rime.cli import register
from rime.ntsb.classify import EXCLUDED_LOCATION, category_for, is_business_jet, region_for
from rime.ntsb.weather_flags import build_flags_from_interim

KEY = ["ev_id", "Aircraft_Key"]
FIRST_YEAR = 1990
OUTPUT = ["ev_id", "Aircraft_Key", "ev_date", "year", "month", "ev_type", "highest_injury",
          "fatal", "region", "category", "is_business_jet", "dec_latitude", "dec_longitude",
          "wx_cond_basic", "wx_involved", "wx_basis", "source_db"]


def assemble(events: pd.DataFrame, aircraft: pd.DataFrame, engines: pd.DataFrame,
             flags: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Returns (in-scope rows, aircraft rows dropped per reason)."""
    first_engine = engines.sort_values("eng_no").drop_duplicates(KEY)[KEY + ["eng_type"]]
    m = (aircraft.merge(first_engine, on=KEY, how="left")
         .merge(events, on="ev_id", how="inner")
         .merge(flags, on=KEY, how="left"))
    m["ev_date"] = pd.to_datetime(m["ev_date"])
    m["year"] = m["ev_date"].dt.year
    m["month"] = m["ev_date"].dt.month
    m["category"] = [category_for(*r) for r in
                     m[["acft_category", "far_part", "eng_type", "unmanned"]].itertuples(index=False)]
    m["region"] = [region_for(c, s) for c, s in zip(m["ev_country"], m["ev_state"])]

    drops: dict[str, int] = {}
    for reason, test in [
        ("non_us", lambda d: d["ev_country"] != "USA"),
        ("pre_1990", lambda d: d["year"] < FIRST_YEAR),
        ("out_of_scope_category", lambda d: d["category"].isna()),
        ("excluded_location", lambda d: d["region"] == EXCLUDED_LOCATION),
    ]:
        bad = test(m)
        drops[reason] = int(bad.sum())
        m = m[~bad]

    m = m.assign(
        highest_injury=m["ev_highest_injury"],
        fatal=m["ev_highest_injury"] == "FATL",
        is_business_jet=[is_business_jet(*r) for r in
                         m[["acft_category", "far_part", "eng_type"]].itertuples(index=False)],
        wx_involved=m["wx_involved"].fillna(False).astype(bool),
        wx_basis=m["wx_basis"].fillna(""),
    )
    return m[OUTPUT].reset_index(drop=True), drops


def counts_by_category_year(events: pd.DataFrame) -> pd.DataFrame:
    """Accident counts per (year, category). The only outcome summary allowed pre-prereg."""
    acc = events[events["ev_type"] == "ACC"]
    g = acc.assign(fatal_wx=acc["fatal"] & acc["wx_involved"]).groupby(["year", "category"])
    return pd.DataFrame({
        "accidents": g.size(),
        "wx_accidents": g["wx_involved"].sum(),
        "fatal_accidents": g["fatal"].sum(),
        "fatal_wx_accidents": g["fatal_wx"].sum(),
    }).astype(int).reset_index()


def _read(table: str, cols: list[str]) -> pd.DataFrame:
    return pd.read_parquet(paths.INTERIM / "ntsb" / f"{table}.parquet", columns=cols)


def build_events() -> pd.DataFrame:
    events = _read("events", ["ev_id", "ev_date", "ev_type", "ev_country", "ev_state",
                              "ev_highest_injury", "dec_latitude", "dec_longitude",
                              "wx_cond_basic", "source_db"])
    aircraft = _read("aircraft", KEY + ["acft_category", "far_part", "unmanned"])
    engines = _read("engines", KEY + ["eng_no", "eng_type"])
    out, drops = assemble(events, aircraft, engines, build_flags_from_interim())
    paths.PROCESSED.mkdir(parents=True, exist_ok=True)
    out.to_parquet(paths.PROCESSED / "events_aircraft.parquet", index=False)
    pd.Series(drops, name="aircraft_rows").to_csv(paths.PROCESSED / "events_drops.csv")
    print(f"  {len(out):,} in-scope aircraft rows; dropped {drops}")
    return out


register("events", build_events, "assemble the in-scope accident table")
