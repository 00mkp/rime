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


def _exact_hits(df: pd.DataFrame, column: str, rules: list[dict], basis) -> pd.DataFrame:
    include = {int(r["code"]) for r in rules if r["column"] == column and r["include"] == "1"}
    codes = pd.to_numeric(df[column], errors="coerce")
    hit = df[codes.isin(include)]
    return pd.DataFrame({"ev_id": hit["ev_id"], "Aircraft_Key": hit["Aircraft_Key"],
                         "basis": basis(hit)})


def weather_flags(findings: pd.DataFrame, events_seq: pd.DataFrame,
                  occurrences: pd.DataFrame, seq_of_events: pd.DataFrame,
                  *, aircraft: pd.DataFrame) -> pd.DataFrame:
    """One row per aircraft in `aircraft`: wx_involved (bool) and wx_basis (';'-joined codes).

    events_seq (post-2008 Events_Sequence) is accepted for interface symmetry; the
    post-2008 rule uses findings only.
    """
    rules = _rules()
    hits = pd.concat([
        _prefix_hits(findings, rules),
        _exact_hits(occurrences, "Occurrence_Code", rules,
                    lambda h: "occ" + h["Occurrence_Code"].astype(str)),
        _exact_hits(seq_of_events, "Subj_Code", rules,
                    lambda h: h["Subj_Code"].astype(str) + "/" + h["Modifier_Code"].astype(str)),
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
        read("Events_Sequence", KEY),
        read("Occurrences", KEY + ["Occurrence_Code"]),
        read("seq_of_events", KEY + ["Subj_Code", "Modifier_Code"]),
        aircraft=read("aircraft", KEY),
    )
