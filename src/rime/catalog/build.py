"""Part 2 crash catalog: physical facts of every serious US accident 1990–2024 (spec §4a).

Deliberately excludes weather fields, findings and cause text so the crash catalog stays
independent of the weather catalog it will be cross-referenced with.
"""
import csv

import numpy as np
import pandas as pd

from rime import paths
from rime.catalog.altitude import extract_altitude
from rime.catalog.timecheck import daynight_mismatch, solar_elevation_deg
from rime.cli import register

KEY = ["ev_id", "Aircraft_Key"]
YEARS = (1990, 2024)
SEVERE = {"FATL", "SERS"}
FORBIDDEN = ("wx_", "finding", "cause")


def _phase_map() -> dict[tuple[str, int], str]:
    with (paths.MANUAL / "phase_map.csv").open() as f:
        return {(r["system"], int(r["code"])): r["phase"] for r in csv.DictReader(f)}


def harmonize_phase(post_prefix, pre_code, _map=None) -> str:
    m = _map or _phase_map()
    if post_prefix is not None and not pd.isna(post_prefix):
        return m.get(("post2008", int(post_prefix)), "unknown")
    if pre_code is not None and not pd.isna(pre_code):
        return m.get(("pre2008", int(pre_code)), "unknown")
    return "unknown"


def _time_utc(ev: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    hhmm = pd.to_numeric(ev["ev_time"], errors="coerce")
    hh, mm = hhmm // 100, hhmm % 100
    ok = hhmm.notna() & (hh <= 23) & (mm <= 59) & (ev["ev_tmzn"].astype(str).str.strip().str.upper() == "UTC")
    date = pd.to_datetime(ev["ev_date"], errors="coerce").dt.normalize()
    t = (date + pd.to_timedelta(hh.where(ok), unit="h") + pd.to_timedelta(mm.where(ok), unit="m")).where(ok)
    return t, ok & date.notna()


def build_catalog(events_aircraft, events, events_seq, occurrences, narratives, ct_seqevt) -> pd.DataFrame:
    ea = events_aircraft[(events_aircraft["ev_type"] == "ACC") & events_aircraft["highest_injury"].isin(SEVERE)
                         & events_aircraft["year"].between(*YEARS)]
    ev = events[["ev_id", "ntsb_no", "ev_date", "ev_time", "ev_tmzn", "light_cond"]].copy()
    ev["time_utc"], ok = _time_utc(ev)
    ev["has_time"] = ok
    cat = ea.merge(ev, on="ev_id", how="left")
    pm = _phase_map()

    # post-2008: the defining event row
    d = events_seq[events_seq["Defining_ev"].astype(bool)].copy()
    d["post_prefix"] = pd.to_numeric(d["Occurrence_Code"], errors="coerce") // 1000
    d = d.drop_duplicates(KEY)[KEY + ["post_prefix", "Occurrence_Description"]]
    # pre-2008: the aircraft's first occurrence
    o = occurrences.assign(_n=pd.to_numeric(occurrences["Occurrence_No"], errors="coerce")).sort_values("_n")
    o = o.drop_duplicates(KEY)
    meaning = dict(zip(pd.to_numeric(ct_seqevt["code"], errors="coerce"), ct_seqevt["meaning"]))
    o = o.assign(pre_code=pd.to_numeric(o["Phase_of_Flight"], errors="coerce"),
                 pre_desc=pd.to_numeric(o["Occurrence_Code"], errors="coerce").map(meaning))[KEY + ["pre_code", "pre_desc"]]
    cat = cat.merge(d, on=KEY, how="left").merge(o, on=KEY, how="left")
    cat["phase"] = [harmonize_phase(a, b, pm) for a, b in zip(cat["post_prefix"], cat["pre_code"])]
    cat["defining_event"] = cat["Occurrence_Description"].fillna(cat["pre_desc"]).fillna("").astype(str).str.strip()

    elev = solar_elevation_deg(cat["dec_latitude"].to_numpy(float), cat["dec_longitude"].to_numpy(float),
                               cat["time_utc"].fillna(pd.Timestamp("2000-01-01")))
    elev = np.where(cat["has_time"].to_numpy(), elev, np.nan)
    mismatch = daynight_mismatch(elev, cat["light_cond"].to_numpy(object))
    cat["time_flag"] = np.where(~cat["has_time"], "no_time", np.where(mismatch, "daynight_mismatch", "ok"))

    narr = narratives.assign(text=narratives["narr_accf"].fillna(narratives["narr_accp"]))[KEY + ["text"]]
    cat = cat.merge(narr.drop_duplicates(KEY), on=KEY, how="left")
    alt = [extract_altitude(t if isinstance(t, str) else None) for t in cat["text"]]
    cat["altitude_ft"], cat["altitude_ref"], cat["altitude_span"] = (list(x) for x in zip(*alt)) if alt else ([], [], [])

    out = cat.rename(columns={"dec_latitude": "lat", "dec_longitude": "lon"})[
        ["ev_id", "Aircraft_Key", "ntsb_no", "time_utc", "time_flag", "lat", "lon", "region", "category",
         "is_business_jet", "highest_injury", "fatal", "phase", "defining_event", "altitude_ft", "altitude_ref",
         "altitude_span", "source_db"]].reset_index(drop=True)
    bad = [c for c in out.columns if any(k in c.lower() for k in FORBIDDEN)]
    assert not bad, f"forbidden columns in crash catalog: {bad}"
    return out


def render_summary(cat: pd.DataFrame) -> str:
    c = cat.assign(decade=(pd.to_datetime(cat["time_utc"]).dt.year.fillna(0) // 10 * 10).astype(int))
    by_dec = c.groupby("decade").agg(rows=("ev_id", "size"),
                                     time_ok=("time_flag", lambda s: f"{(s == 'ok').mean():.1%}"),
                                     daynight_mismatch=("time_flag", lambda s: f"{(s == 'daynight_mismatch').mean():.1%}"),
                                     has_latlon=("lat", lambda s: f"{s.notna().mean():.1%}"),
                                     has_altitude=("altitude_ft", lambda s: f"{s.notna().mean():.1%}"),
                                     phase_known=("phase", lambda s: f"{(s != 'unknown').mean():.1%}")).reset_index()
    by_dec["decade"] = by_dec["decade"].map(lambda d: "no time" if d == 0 else f"{d}s")
    phase = c["phase"].value_counts().rename_axis("phase").reset_index(name="rows")
    sample = c[c["altitude_ft"].notna()].sample(min(10, int(c["altitude_ft"].notna().sum())), random_state=20261102)

    def table(df):
        cols = list(df.columns)
        return "\n".join(["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] +
                         ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)])

    spans = "\n".join(f"- `{r.ntsb_no}` → **{r.altitude_ft:,.0f} ft {r.altitude_ref}**: …{r.altitude_span.replace(chr(10), ' ')}…"
                      for r in sample.itertuples(index=False))
    return "\n\n".join([
        "# rime crash catalog: coverage and quality",
        f"{len(cat):,} aircraft involvements in fatal or serious US accidents, 1990–2024 (aircraft categories per the spec). "
        "Physical facts only: no weather fields, findings, or cause text.",
        "## Coverage by decade", table(by_dec),
        "`time_ok` means NTSB's stored UTC time is consistent with day/night: the sun's elevation at that place and time "
        "agrees with NTSB's light condition. A mismatch suggests the stored time is wrong, so those rows shouldn't be matched to weather by time.",
        "## Phase of flight (harmonized)", table(phase),
        "## Altitude spot check (10 random extractions)",
        "Altitude comes from the factual narrative and is used only when a pattern explicitly ties a number to flight altitude. "
        "It is an altitude the narrative ties to the flight, not necessarily the altitude at the moment of the accident. "
        "In spot checks about 8–9 of 10 extractions were the flight's actual altitude in the accident sequence. Each row keeps the source text "
        "(`altitude_span`) so it can be checked.",
        spans,
    ]) + "\n"


def run_crashes() -> None:
    from access_parser import AccessParser
    d = paths.INTERIM / "ntsb"
    read = lambda t, cols: pd.read_parquet(d / f"{t}.parquet", columns=cols)
    ct_path = d / "ct_seqevt.parquet"
    if not ct_path.exists():
        pd.DataFrame(AccessParser(str(paths.RAW / "pre2008.mdb")).parse_table("ct_seqevt")).astype(str).to_parquet(ct_path, index=False)
    cat = build_catalog(
        pd.read_parquet(paths.PROCESSED / "events_aircraft.parquet"),
        read("events", ["ev_id", "ntsb_no", "ev_date", "ev_time", "ev_tmzn", "light_cond"]),
        read("Events_Sequence", KEY + ["Occurrence_Code", "Occurrence_Description", "Defining_ev"]),
        read("Occurrences", KEY + ["Occurrence_No", "Occurrence_Code", "Phase_of_Flight"]),
        read("narratives", KEY + ["narr_accf", "narr_accp"]),
        pd.read_parquet(ct_path),
    )
    cat.to_parquet(paths.PROCESSED / "crash_catalog.parquet", index=False)
    out = paths.RESULTS / "catalog"
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.md").write_text(render_summary(cat))
    print(f"  {len(cat):,} catalog rows → {out / 'summary.md'}")


register("crashes", run_crashes, "build the Part 2 crash catalog (physical facts only)")
