"""Hazard-specific accident classes (prereg H2 table) and the H3 en-route crosswalk."""
import csv
from itertools import product

import pandas as pd

from rime import paths
from rime.cli import register

KEY = ["ev_id", "Aircraft_Key"]
HAZARDS = ("icing", "turbulence", "convective")
H3_CATEGORIES = ("airliner", "charter", "ga_turbine")


def _rows(name: str) -> list[dict]:
    with (paths.MANUAL / name).open() as f:
        return list(csv.DictReader(f))


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.strip(), errors="coerce")


def _prefix_decider(rules: list[dict]):
    pref = sorted((r for r in rules if r["match"] == "prefix"), key=lambda r: -len(r["code"]))

    def decide(code) -> bool:
        code = "" if code is None else str(code)
        for r in pref:
            if code.startswith(r["code"]):
                return r["include"] == "1"
        return False
    return decide


def hazard_flags(findings: pd.DataFrame, events_seq: pd.DataFrame, seq_of_events: pd.DataFrame,
                 *, aircraft: pd.DataFrame) -> pd.DataFrame:
    rules = _rows("hazard_codes.csv")
    out = aircraft[KEY].drop_duplicates().reset_index(drop=True)
    occ3 = _num(events_seq["Occurrence_Code"]) % 1000
    subj, mod = _num(seq_of_events["Subj_Code"]), _num(seq_of_events["Modifier_Code"])
    for hz in HAZARDS:
        r = [x for x in rules if x["hazard"] == hz]
        decide = _prefix_decider(r)
        hit_f = findings[findings["finding_code"].map(decide).astype(bool)][KEY]
        last3 = {int(x["code"]) for x in r if x["match"] == "last3" and x["include"] == "1"}
        hit_e = events_seq[occ3.isin(last3)][KEY]
        pairs = [tuple(map(int, x["code"].split(":"))) for x in r if x["match"] == "subj_mod" and x["include"] == "1"]
        m = pd.Series(False, index=seq_of_events.index)
        for s_, m_ in pairs:
            m |= (subj == s_) & (mod == m_)
        hit_s = seq_of_events[m][KEY]
        hits = pd.concat([hit_f, hit_e, hit_s]).drop_duplicates().assign(**{hz: True})
        out = out.merge(hits, on=KEY, how="left")
        out[hz] = out[hz].fillna(False).astype(bool)
    return out


def enroute_flags(events_seq: pd.DataFrame, occurrences: pd.DataFrame, *, aircraft: pd.DataFrame) -> pd.DataFrame:
    codes = _rows("phase_codes.csv")
    post = {int(c["code"]) for c in codes if c["system"] == "post2008" and c["enroute"] == "1"}
    pre = {int(c["code"]) for c in codes if c["system"] == "pre2008" and c["enroute"] == "1"}
    hit_e = events_seq[(_num(events_seq["Occurrence_Code"]) // 1000).isin(post)][KEY]
    hit_o = occurrences[_num(occurrences["Phase_of_Flight"]).isin(pre)][KEY]
    hits = pd.concat([hit_e, hit_o]).drop_duplicates().assign(enroute=True)
    out = aircraft[KEY].drop_duplicates().merge(hits, on=KEY, how="left")
    out["enroute"] = out["enroute"].fillna(False).astype(bool)
    return out


def hazard_counts(events: pd.DataFrame, flags: pd.DataFrame, enroute: pd.DataFrame) -> pd.DataFrame:
    acc = events[events["ev_type"] == "ACC"].merge(flags, on=KEY, how="left").merge(enroute, on=KEY, how="left")
    for c in (*HAZARDS, "enroute"):
        acc[c] = acc[c].fillna(False).astype(bool)
    acc["h3"] = acc["category"].isin(H3_CATEGORIES) & acc["enroute"] & acc[list(HAZARDS)].any(axis=1)
    long = acc.melt(id_vars=["year", "category"], value_vars=[*HAZARDS, "h3"], var_name="hazard", value_name="hit")
    counts = long[long["hit"]].groupby(["year", "category", "hazard"]).size().rename("count")
    grid = pd.DataFrame(list(product(sorted(events["year"].unique()), sorted(events["category"].unique()),
                                     [*HAZARDS, "h3"])), columns=["year", "category", "hazard"])
    out = grid.merge(counts.reset_index(), on=["year", "category", "hazard"], how="left")
    out["count"] = out["count"].fillna(0).astype(int)
    return out


def flags_from_interim() -> tuple[pd.DataFrame, pd.DataFrame]:
    d = paths.INTERIM / "ntsb"
    read = lambda t, cols: pd.read_parquet(d / f"{t}.parquet", columns=cols)
    aircraft = read("aircraft", KEY)
    es = read("Events_Sequence", KEY + ["Occurrence_Code"])
    flags = hazard_flags(read("Findings", KEY + ["finding_code"]), es,
                         read("seq_of_events", KEY + ["Subj_Code", "Modifier_Code"]), aircraft=aircraft)
    enr = enroute_flags(es, read("Occurrences", KEY + ["Phase_of_Flight"]), aircraft=aircraft)
    return flags, enr


def build_hazards() -> None:
    events = pd.read_parquet(paths.PROCESSED / "events_aircraft.parquet")
    flags, enr = flags_from_interim()
    out = hazard_counts(events, flags, enr)
    out.to_parquet(paths.PROCESSED / "hazard_counts.parquet", index=False)
    tot = out.groupby("hazard")["count"].sum().to_dict()
    print(f"  hazard accident involvements (all years, in-scope): {tot}")


register("hazards", build_hazards, "hazard-specific accident counts (icing, turbulence, convective, H3)")
