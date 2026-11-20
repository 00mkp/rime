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
# Defining/first events that describe investigator-attributed weather are withheld from the text
WEATHER_EVENT_POST = {210, 360, 362, 390, 400, 401, 402}   # Events_Sequence last 3 digits
WEATHER_EVENT_PRE = {240, 330}                              # Occurrences.Occurrence_Code
CHECKABLE_LIGHT = {"DAYL", "NITE", "NDRK", "NBRT"}


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
    d["post_wx"] = (pd.to_numeric(d["Occurrence_Code"], errors="coerce") % 1000).isin(WEATHER_EVENT_POST)
    d = d.drop_duplicates(KEY)[KEY + ["post_prefix", "Occurrence_Description", "post_wx"]]
    # pre-2008: the aircraft's first occurrence
    o = occurrences.assign(_n=pd.to_numeric(occurrences["Occurrence_No"], errors="coerce")).sort_values("_n")
    o = o.drop_duplicates(KEY)
    meaning = dict(zip(pd.to_numeric(ct_seqevt["code"], errors="coerce"), ct_seqevt["meaning"]))
    occ_code = pd.to_numeric(o["Occurrence_Code"], errors="coerce")
    o = o.assign(pre_code=pd.to_numeric(o["Phase_of_Flight"], errors="coerce"), pre_desc=occ_code.map(meaning),
                 pre_wx=occ_code.isin(WEATHER_EVENT_PRE))[KEY + ["pre_code", "pre_desc", "pre_wx"]]
    cat = cat.merge(d, on=KEY, how="left").merge(o, on=KEY, how="left")
    cat["phase"] = [harmonize_phase(a, b, pm) for a, b in zip(cat["post_prefix"], cat["pre_code"])]
    cat["defining_event"] = cat["Occurrence_Description"].fillna(cat["pre_desc"]).fillna("").astype(str).str.strip()
    withheld = cat["post_wx"].fillna(False).astype(bool) | (cat["post_prefix"].isna() & cat["pre_wx"].fillna(False).astype(bool))
    cat.loc[withheld, "defining_event"] = ""  # investigator-attributed weather stays out of the crash catalog

    elev = solar_elevation_deg(cat["dec_latitude"].to_numpy(float), cat["dec_longitude"].to_numpy(float),
                               cat["time_utc"].fillna(pd.Timestamp("2000-01-01")))
    elev = np.where(cat["has_time"].to_numpy(), elev, np.nan)
    mismatch = daynight_mismatch(elev, cat["light_cond"].to_numpy(object))
    checkable = np.isfinite(elev) & cat["light_cond"].fillna("").astype(str).str.strip().str.upper().isin(CHECKABLE_LIGHT).to_numpy()
    cat["time_flag"] = np.select([~cat["has_time"].to_numpy(), mismatch, ~checkable],
                                 ["no_time", "daynight_mismatch", "unchecked"], "ok")

    narr = narratives.assign(text=narratives["narr_accf"].fillna(narratives["narr_accp"]))[KEY + ["text"]]
    cat = cat.merge(narr.drop_duplicates(KEY), on=KEY, how="left")
    alt = [extract_altitude(t if isinstance(t, str) else None) for t in cat["text"]]
    cat["altitude_ft"], cat["altitude_ref"], cat["altitude_span"] = (list(x) for x in zip(*alt)) if alt else ([], [], [])

    out = cat.rename(columns={"dec_latitude": "lat", "dec_longitude": "lon"})[
        ["ev_id", "Aircraft_Key", "ntsb_no", "time_utc", "time_flag", "lat", "lon", "region", "category",
         "is_business_jet", "highest_injury", "fatal", "phase", "defining_event", "altitude_ft", "altitude_ref",
         "altitude_span", "source_db"]].reset_index(drop=True)
    bad = [c for c in out.columns if any(k in c.lower() for k in FORBIDDEN)]
    if bad:
        raise ValueError(f"forbidden columns in crash catalog: {bad}")
    return out


def _table(df) -> str:
    cols = list(df.columns)
    return "\n".join(["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)] +
                     ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)])


def _coverage(g) -> pd.DataFrame:
    pct = lambda f: (lambda s: f"{f(s).mean():.1%}")
    return g.agg(rows=("ev_id", "size"),
                 time_ok=("time_flag", pct(lambda s: s == "ok")),
                 time_unchecked=("time_flag", pct(lambda s: s == "unchecked")),
                 daynight_mismatch=("time_flag", pct(lambda s: s == "daynight_mismatch")),
                 has_latlon=("lat", pct(lambda s: s.notna())),
                 has_altitude=("altitude_ft", pct(lambda s: s.notna())),
                 phase_known=("phase", pct(lambda s: s != "unknown"))).reset_index()


def render_summary(cat: pd.DataFrame) -> str:
    c = cat.assign(decade=(pd.to_datetime(cat["time_utc"]).dt.year.fillna(0) // 10 * 10).astype(int))
    by_dec = _coverage(c.groupby("decade"))
    by_dec["decade"] = by_dec["decade"].map(lambda d: "no time" if d == 0 else f"{d}s")
    by_cat = _coverage(c.groupby("category"))
    phase_src = (c.groupby(["phase", "source_db"]).size().unstack(fill_value=0)
                 .apply(lambda col: (col / col.sum()).map(lambda v: f"{v:.1%}")).reset_index())
    n_alt = int(c["altitude_ft"].notna().sum())
    sample = c[c["altitude_ft"].notna()].sample(min(10, n_alt), random_state=20261102) if n_alt else c.head(0)
    spans = "\n".join(f"- `{r.ntsb_no}` → **{r.altitude_ft:,.0f} ft {r.altitude_ref}**: …{str(r.altitude_span).replace(chr(10), ' ')}…"
                      for r in sample.itertuples(index=False))
    return "\n\n".join([
        "# rime crash catalog: coverage and quality",
        f"{len(cat):,} aircraft involvements in fatal or serious US accidents, 1990–2024, in the spec's aircraft categories. "
        "Physical facts only: no weather fields, findings, or cause text. Where the defining (post-2008) or first (pre-2008) "
        f"event is an investigator-attributed weather encounter ({int(((c['defining_event'] == '') & (c['phase'] != 'unknown')).sum()):,} rows, "
        "e.g. 'VFR encounter with IMC'), the event text is withheld. The phase is kept.",
        "## Coverage by decade", _table(by_dec),
        "## Coverage by aircraft category", _table(by_cat),
        "## How good are the times?",
        "NTSB stores event times in UTC. `ok` means the time was checked and is consistent with NTSB's day/night code: the sun's "
        "elevation at that place and time agrees with day or night. `unchecked` means no check was possible (no coordinates, or "
        "twilight/unknown light condition). `daynight_mismatch` means the stored time is likely wrong.",
        "The mismatch rate is only a **lower bound** on time errors. Shifting every time artificially shows that the check catches "
        "about 2–4% of 1-hour errors, 8–10% of 2-hour errors, and 15–17% of 3-hour errors. It can't see **24-hour date errors** at all, "
        "and those exist: an evening local time stored with the local date instead of the next UTC date (e.g. Pinnacle 3701, "
        "DCA01MA017). Spot checks against narrative local times suggest a few percent of rows are off by an hour or more. "
        "Any weather matching must use time windows of several hours and a date-shift sensitivity check.",
        "## Phase by source database (harmonized phase, share of rows)",
        "Post-2008 uses the phase of NTSB's *defining event*; pre-2008 uses the phase of the aircraft's *first occurrence*. "
        "The two are close but not identical, so compare across 2008 with care.",
        _table(phase_src),
        "## Altitude spot check (10 random extractions)",
        "Altitude comes from the factual narrative and is used only when a pattern explicitly ties a number to flight altitude, "
        "excluding density altitude, airport/field elevation, forecasts, and guidance. It is an altitude the narrative ties to the "
        "flight, not necessarily the altitude at the moment of the accident. On 2026-11-19 a reviewer checked 22 spans and found 19 correct "
        "(about 86%); the three errors (two density altitudes, one airport elevation) are now excluded. Each row keeps its source text "
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
