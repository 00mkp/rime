"""Weather-involvement flag per aircraft, harmonized across NTSB's 2008 coding change."""
import csv

import pandas as pd

from rime import paths

KEY = ["ev_id", "Aircraft_Key"]


def _rules() -> list[dict]:
    with (paths.MANUAL / "wx_codes.csv").open() as f:
        return list(csv.DictReader(f))


def _prefix_hits(findings: pd.DataFrame, rules: list[dict]) -> pd.DataFrame:
    """Longest matching prefix decides include/exclude for each finding code."""
    pref = sorted((r for r in rules if r["match"] == "prefix"), key=lambda r: -len(r["code"]))

    def decide(code) -> bool:
        code = "" if code is None else str(code)
        for r in pref:
            if code.startswith(r["code"]):
                return r["include"] == "1"
        return False

    hit = findings[findings["finding_code"].map(decide).astype(bool)]
    return pd.DataFrame({"ev_id": hit["ev_id"], "Aircraft_Key": hit["Aircraft_Key"],
                         "basis": hit["finding_code"].astype(str)})


def _included(rules: list[dict], match: str) -> list[str]:
    return [r["code"] for r in rules if r["match"] == match and r["include"] == "1"]


def _exact_hits(df: pd.DataFrame, column: str, rules: list[dict], basis) -> pd.DataFrame:
    include = {int(c) for c in _included(rules, "exact")
               if any(r["column"] == column and r["code"] == c for r in rules)}
    codes = pd.to_numeric(df[column], errors="coerce")
    hit = df[codes.isin(include)]
    return pd.DataFrame({"ev_id": hit["ev_id"], "Aircraft_Key": hit["Aircraft_Key"],
                         "basis": basis(hit)})


def _last3_hits(events_seq: pd.DataFrame, rules: list[dict]) -> pd.DataFrame:
    """Post-2008 Events_Sequence codes are 3-digit phase + 3-digit occurrence."""
    include = {int(c) for c in _included(rules, "last3")}
    codes = pd.to_numeric(events_seq["Occurrence_Code"], errors="coerce")
    hit = events_seq[(codes % 1000).isin(include)]
    return pd.DataFrame({"ev_id": hit["ev_id"], "Aircraft_Key": hit["Aircraft_Key"],
                         "basis": "seq" + hit["Occurrence_Code"].astype(str)})


def _subject_modifier_hits(seq: pd.DataFrame, rules: list[dict]) -> pd.DataFrame:
    """Pre-2008 'code' = 'SUBJ:LO-HI' — subject code with a modifier in [LO, HI]."""
    mask = pd.Series(False, index=seq.index)
    subj = pd.to_numeric(seq["Subj_Code"], errors="coerce")
    mod = pd.to_numeric(seq["Modifier_Code"], errors="coerce")
    for code in _included(rules, "subject_modifier"):
        s_, rng = code.split(":")
        lo, hi = map(int, rng.split("-"))
        mask |= (subj == int(s_)) & mod.between(lo, hi)
    hit = seq[mask]
    return pd.DataFrame({"ev_id": hit["ev_id"], "Aircraft_Key": hit["Aircraft_Key"],
                         "basis": hit["Subj_Code"].astype(str) + "/" + hit["Modifier_Code"].astype(str)})


def weather_flags(findings: pd.DataFrame, events_seq: pd.DataFrame,
                  occurrences: pd.DataFrame, seq_of_events: pd.DataFrame,
                  *, aircraft: pd.DataFrame) -> pd.DataFrame:
    """One row per aircraft in `aircraft`: wx_involved (bool) and wx_basis (';'-joined codes).

    Post-2008: weather findings (0303*) or weather occurrences in Events_Sequence.
    Pre-2008: weather-condition subject with a weather modifier, or weather occurrences.
    """
    rules = _rules()
    hits = pd.concat([
        _prefix_hits(findings, rules),
        _exact_hits(occurrences, "Occurrence_Code", rules,
                    lambda h: "occ" + h["Occurrence_Code"].astype(str)),
        _last3_hits(events_seq, rules),
        _subject_modifier_hits(seq_of_events, rules),
    ], ignore_index=True)
    basis = (hits.drop_duplicates().groupby(KEY)["basis"]
             .agg(lambda s: ";".join(sorted(s))).rename("wx_basis").reset_index())
    out = aircraft[KEY].drop_duplicates().merge(basis, on=KEY, how="left")
    out["wx_basis"] = out["wx_basis"].fillna("")
    out["wx_involved"] = out["wx_basis"] != ""
    return out


def build_flags_from_interim() -> pd.DataFrame:
    d = paths.INTERIM / "ntsb"
    read = lambda t, cols=None: pd.read_parquet(d / f"{t}.parquet", columns=cols)
    return weather_flags(
        read("Findings", KEY + ["finding_code"]),
        read("Events_Sequence", KEY + ["Occurrence_Code"]),
        read("Occurrences", KEY + ["Occurrence_Code"]),
        read("seq_of_events", KEY + ["Subj_Code", "Modifier_Code"]),
        aircraft=read("aircraft", KEY),
    )
