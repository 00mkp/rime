"""Build data/manual/exposure_annual.csv: annual US flight hours by aircraft category.

Re-runnable extraction for every year whose source is a spreadsheet (FAA GA & Part 135
Activity Survey chapter 3 workbooks, NTSB exposure workbooks). Years that exist only as
PDF/HTML tables are hand-transcribed in data/manual/exposure_transcribed.csv and merged in.
Definitions, per-year sources, derivations and known gaps: data/manual/EXPOSURE_SOURCES.md.

    uv run python scripts/curate_exposure.py

Downloads are cached under data/raw/exposure/ (gitignored) via rime.download.fetch.
"""
from __future__ import annotations

import re
import sys
import warnings

import pandas as pd

from rime import paths
from rime.download import fetch
from rime.exposure import COLUMNS, load_exposure

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

FAA = "https://www.faa.gov"
FAA_GA = f"{FAA}/sites/faa.gov/files/data_research/aviation_data_statistics/general_aviation"
NTSB = "https://www.ntsb.gov/safety"

# FAA GA & Part 135 Activity Survey, chapter III workbook ("Primary and Actual Use"), sheet with
# Table 3.2 "Total Hours Flown by Actual Use by Aircraft Type". No survey was run for CY2011.
FAA_CH3 = {
    2000: f"{FAA_GA}/cy2000/2000%2520GA%2520tab_3-2.xls",
    2001: f"{FAA_GA}/cy2001/2001%2520Table%25203.2.xls",
    2002: f"{FAA}/2002_GA_Survey_Chapter_3",
    2003: f"{FAA}/2003_GA_Survey_Chapter_3",
    2004: f"{FAA_GA}/cy2004/FAA_2004_3.xls",
    2005: f"{FAA_GA}/cy2005/FAA_2005_3.xls",
    2006: f"{FAA}/2006_GA_Survey_Chapter_3",
    2007: f"{FAA}/2007_GA_Survey_Chapter_3",
    2008: f"{FAA}/2008_GA_Survey_Chapter_3",
    2009: f"{FAA}/2009_GA_Survey_Chapter_3",
    2010: f"{FAA_GA}/cy2010/2010_GA_Survey_Chapter3_23DEC2011V3.xls",
    2012: f"{FAA_GA}/cy2012/2012-GA-Survey-Chapter-3-Tables-16Dec2013-V2.xls",
    2013: f"{FAA_GA}/cy2013/2013_GA_Survey_Chapter_3_Tables.xlsx",
    2014: f"{FAA_GA}/cy2014/2014-GA-Survey-Chapter-3-Tables_org.xlsx",
    2015: f"{FAA_GA}/cy2015/2015_GA_Survey_Chapter_3_Tables_16SEP2016V2.xlsx",
    2016: f"{FAA}/media/72656",
    2017: f"{FAA_GA}/cy2017/2017_GA_Survey_Chapter3_Tables_3Dec2018_508_Compliant_V1.xlsx",
    2018: f"{FAA_GA}/cy2018/2018GASurvey_Chapter_3_Tables_508_Compliant_12DEC2019V1_(002)-1.xlsx",
    2019: f"{FAA_GA}/cy2019/2019GASurvey_Chapter_3_Tables_508_Compliant_24NOV2020V1.xlsx",
    2020: f"{FAA_GA}/cy2020/2020GASurvey_Chapter_3_Tables_508_Compliant_03DEC2021V1.xlsx",
    2021: f"{FAA}/sites/faa.gov/files/2021GASurveyCh3_508Compliant_17JAN2023V1.xlsx",
    2022: f"{FAA}/sites/faa.gov/files/2022GASurveyCh3_508Compliant_08DEC2023V1.xlsx",
    2023: f"{FAA}/sites/faa.gov/files/2023GASurveyCh3_508Compliant_04DEC2024V1.xlsx",
    2024: f"{FAA}/data_research/aviation_data_statistics/general_aviation/cy2024/2024GASurveyCh3.xlsx",
}
# Latest chapter I, Table 1.3 (total hours by aircraft type, 2013-2024): used only as a cross-check.
FAA_CH1_LATEST = (2024, f"{FAA}/data_research/aviation_data_statistics/general_aviation/cy2024/2024GASurveyCh1.xlsx")

NTSB_STATS = f"{NTSB}/Documents/AviationAccidentStatistics_2005-2024_20260112.xlsx"
NTSB_AR = {
    ("2013", "121"): f"{NTSB}/data/Documents/datafiles/AnnualReview_2013_Public_2_Part121_20150218.xls",
    ("2013", "135"): f"{NTSB}/data/Documents/datafiles/AnnualReview_2013_Public_3_Part135_20150218.xls",
    ("2012", "121"): f"{NTSB}/data/Documents/datafiles/AnnualReview_2012_Public_2_Part121_20140113_Final.xlsx",
    ("2019", "121"): f"{NTSB}/data/Documents/datafiles/AnnualReview_2019_Public_2_Part121_20211215.xlsx",
    ("2019", "135"): f"{NTSB}/data/Documents/datafiles/AnnualReview_2019_Public_3_Part135_20211215.xlsx",
}

LABELS = {
    "fw": ["Fixed Wing: Total"],
    "piston": ["Piston: Total"],
    "turboprop": ["Turboprop: Total"],
    # 2006-2007 have no "Turbojet: Total" row; the "Fixed Wing - Turbojet" heading carries the values.
    "turbojet": ["Turbojet: Total", "Fixed Wing - Turbojet"],
    "rotor": ["Rotorcraft: Total", "Rotocraft: Total"],
    "exp": ["Experimental: Total"],
    # 2005-08 "Light-sport"; 2009-10 "Light-sport: Total" (= experimental + special LSA, not in
    # Experimental: Total); 2012+ only "Special Light-sport" (experimental LSA is inside Experimental: Total).
    "lsa": ["Light-sport: Total", "Light-sport", "Special Light-sport"],
}


def _ext(url: str, year: int) -> str:
    return ".xlsx" if url.endswith(".xlsx") or year == 2016 else ".xls"


def get(url: str, name: str):
    (paths.RAW / "exposure").mkdir(parents=True, exist_ok=True)
    return fetch(url, f"exposure/{name}")


def read(path, sheet) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet, header=None, engine="calamine")


def num(v) -> float | None:
    """Cell -> float; suppressed ('*', '**') or blank -> None."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def headers(df: pd.DataFrame) -> list[str]:
    col0 = [("" if pd.isna(v) else str(v).strip()) for v in df.iloc[:, 0]]
    first = next(i for i, v in enumerate(col0) if v.lower().startswith("fixed wing"))
    return [" ".join(str(v).strip() for v in df.iloc[:first, j] if not pd.isna(v) and str(v).strip())
            for j in range(df.shape[1])]


def est_row(df: pd.DataFrame, labels: list[str]) -> list | None:
    """Values of the 'Est. Total Hours' row directly under the first matching row label."""
    col0 = [("" if pd.isna(v) else str(v).strip()) for v in df.iloc[:, 0]]
    for lab in labels:
        for i, v in enumerate(col0):
            if v.lower() != lab.lower():
                continue
            nxt = next((j for j in range(i + 1, len(col0)) if col0[j]), None)
            if nxt is not None and col0[nxt].startswith("Est. Total Hours"):
                return df.iloc[nxt].tolist()
    return None


def survey_layout(year: int, df: pd.DataFrame) -> dict:
    """Column indices for: total (all uses), Part 135 use columns, optional GA-only total."""
    h = headers(df)
    n = df.shape[1]
    if year <= 2003:
        taxi = [j for j, s in enumerate(h) if "Air Taxi" in s]
        tours = [j for j, s in enumerate(h) if "Air Tours" in s]
        assert len(taxi) == 1 and len(tours) == 1, (year, h)
        return {"total": 2, "p135": [taxi[0], tours[0]], "ga": None}
    if year <= 2015:
        assert "Total" in h[2], (year, h[2])
        assert "Taxi" in h[n - 3] and "Tours" in h[n - 2] and "Med" in h[n - 1], (year, h[-3:])
        return {"total": 2, "p135": [n - 3, n - 2, n - 1], "ga": None}
    if year <= 2022:
        # Column 1 is headed "General Aviation Use Total Active" but holds the all-use total
        # (it equals Ch.1 Table 1.3 and GA uses + Part 135 uses); checked in cross_check_ch1().
        assert "Total Active" in h[1] and all("Part 135" in h[j] for j in (n - 3, n - 2, n - 1)), (year, h)
        return {"total": 1, "p135": [n - 3, n - 2, n - 1], "ga": None}
    if year == 2023:
        # Header row is misaligned with the 19 data columns. Data layout (verified by the
        # identities total = GA total + Part 135 total, and Part 135 total = taxi + tours + med):
        # 1 total, 2-13 GA uses, 14 GA total, 15-17 Part 135 taxi/tours/med, 18 Part 135 total.
        assert n == 19, (year, n)
        return {"total": 1, "p135": [15, 16, 17], "ga": 14, "p135_total": 18}
    assert h[1].strip() == "Total Active" and "General Aviation Use Total" in h[2] and "Part 135 Total" in h[15], (year, h)
    return {"total": 1, "p135": [16, 17, 18], "ga": 2, "p135_total": 15}


def survey_rows(year: int) -> tuple[list[dict], dict]:
    url = FAA_CH3[year]
    path = get(url, f"faa_cy{year}_ch3{_ext(url, year)}")
    xl = pd.ExcelFile(path, engine="calamine")
    sheet = "3.2" if "3.2" in xl.sheet_names else xl.sheet_names[0]
    df = read(path, sheet)
    lay = survey_layout(year, df)
    rows = {k: est_row(df, labs) for k, labs in LABELS.items()}
    for k in ("fw", "piston", "turboprop", "turbojet", "rotor", "exp"):
        assert rows[k] is not None, (year, k)
    if year >= 2005:
        assert rows["lsa"] is not None, (year, "lsa")

    t = lay["total"]
    tot = {k: (num(r[t]) if r is not None else 0.0) for k, r in rows.items()}
    fw_sum = tot["piston"] + tot["turboprop"] + tot["turbojet"]
    assert abs(tot["fw"] - fw_sum) <= 2, (year, tot["fw"], fw_sum)  # FW = piston + turboprop + turbojet
    notes = []

    if lay.get("ga") is not None:
        g, pt = lay["ga"], lay["p135_total"]
        for k in ("piston", "turboprop", "turbojet", "rotor"):
            assert abs(num(rows[k][t]) - num(rows[k][g]) - num(rows[k][pt])) <= 2, (year, k)
        ga = {k: num(rows[k][g]) for k in ("piston", "turboprop", "turbojet")}
        fw135 = num(rows["fw"][pt])
        rot135 = num(rows["rotor"][pt])
        method = f"GA-use total column (col {g})"
    else:
        # Part 135 hours per type = sum over the Part 135 use columns. A suppressed piston cell is
        # recovered from the fixed-wing row: piston = FW - turboprop - turbojet (exact when it is the
        # only suppressed cell in that column). Turbine Part 135 = FW Part 135 - piston Part 135.
        p135 = 0.0
        fw135 = 0.0
        for c, use in zip(lay["p135"], ("Air Taxi", "Air Tours", "Air Med")):
            fw = num(rows["fw"][c])
            assert fw is not None, (year, "fw suppressed", c)
            fw135 += fw
            p, tp, tj = (num(rows[k][c]) for k in ("piston", "turboprop", "turbojet"))
            if p is None:
                known = sum(v for v in (tp, tj) if v is not None)
                resid = fw - known
                others = [k for k, v in (("turboprop", tp), ("turbojet", tj)) if v is None]
                if not others:
                    p = resid
                    notes.append(f"piston Part 135 {use} suppressed so derived as FW-TP-TJ={p:.0f}")
                else:
                    w = {k: tot[k] for k in ["piston", *others]}
                    p = resid * w["piston"] / sum(w.values())
                    notes.append(f"piston+{'+'.join(others)} Part 135 {use} suppressed; FW residual {resid:.0f} "
                                 f"split by type total hours (piston share {p:.0f})")
            p135 += p
        ga = {"piston": tot["piston"] - p135,
              "turbine": tot["turboprop"] + tot["turbojet"] - (fw135 - p135)}
        rot135 = sum(num(rows["rotor"][c]) or 0.0 for c in lay["p135"])
        cols = "Air Taxi + Air Tours" if year <= 2003 else "On-Demand Part 135 Air Taxi + Air Tours + Air Med"
        method = f"total minus {cols} use"

    turbine_ga = ga["turbine"] if "turbine" in ga else ga["turboprop"] + ga["turbojet"]
    lsa = tot["lsa"] if rows["lsa"] is not None else 0.0
    cite = f"FAA GA Survey CY{year} Table 3.2 (sheet {sheet})"
    note = ("; " + "; ".join(notes)) if notes else ""
    out = [
        {"year": year, "category": "ga_piston", "flight_hours": ga["piston"] + tot["exp"] + lsa,
         "source": f"{cite}: Piston {method} + Experimental Total" + (" + Light-sport" if year >= 2005 else "") + note},
        {"year": year, "category": "ga_turbine", "flight_hours": turbine_ga,
         "source": f"{cite}: Turboprop + Turbojet {method}" + note},
        {"year": year, "category": "helicopter", "flight_hours": tot["rotor"],
         "source": f"{cite}: Rotorcraft Total (all uses)"},
    ]
    for r in out:
        r["source_url"] = url
        r["departures"] = None
    return out, {"fw135": fw135, "rot135": rot135, "tot": tot}


def ntsb_table(path, sheet: str, want: dict[str, str]) -> dict[int, dict[str, float]]:
    """{year: {key: value}} from an NTSB statistics table; want maps key -> column-header prefix."""
    df = read(path, sheet)
    col0 = [("" if pd.isna(v) else str(v).strip()) for v in df.iloc[:, 0]]
    hdr_i = col0.index("Year")
    hdr = [("" if pd.isna(v) else str(v).strip()) for v in df.iloc[hdr_i]]
    idx = {k: next(j for j, s in enumerate(hdr) if s.startswith(p)) for k, p in want.items()}
    out = {}
    for i in range(hdr_i + 1, len(col0)):
        m = re.fullmatch(r"(\d{4})\D?", col0[i])
        if not m:
            continue
        vals = {k: num(df.iat[i, j]) for k, j in idx.items()}
        out[int(m.group(1))] = vals
    return out


def ar_sheet(path, sheet: str, col: int = 1, scale: float = 1e6) -> dict[int, float]:
    """NTSB Annual Review exposure sheet: 'Calendar Year' column + values in millions."""
    df = read(path, sheet)
    out = {}
    for _, r in df.iterrows():
        m = re.fullmatch(r"(\d{4})\*?", str(r.iloc[0]).strip())
        v = num(r.iloc[col]) if df.shape[1] > col else None
        if m and v is not None:
            out[int(m.group(1))] = round(v * scale)
    return out


def ntsb_rows() -> tuple[list[dict], dict]:
    stats = get(NTSB_STATS, "ntsb_stats_2005_2024.xlsx")
    t5 = ntsb_table(stats, "Table 5", {"hours": "Flight Hours", "deps": "Departures"})
    t8 = ntsb_table(stats, "Table 8", {"hours": "Flight Hours"})
    t17 = ntsb_table(stats, "Table 17", {"hours": "Flight Hours"})
    t20 = ntsb_table(stats, "Table 20", {"hours": "Flight Hours"})
    rows = []
    s = "NTSB US Civil Aviation Accident Statistics 2005-2024"
    for y, v in sorted(t5.items()):
        rows.append({"year": y, "category": "airliner", "flight_hours": v["hours"], "departures": v["deps"],
                     "source": f"{s} Table 5 (Part 121 sched+nonsched)", "source_url": NTSB_STATS})
    for y in sorted(t8):
        c, od = t8[y]["hours"], t17.get(y, {}).get("hours")
        if c is None or od is None:
            continue  # on-demand hours not estimated (2011: no FAA survey)
        rows.append({"year": y, "category": "charter", "flight_hours": c + od, "departures": None,
                     "source": f"{s} Table 8 (Part 135 commuter) + Table 17 (on-demand fixed-wing); "
                               f"fixed-wing split given by FAA survey", "source_url": NTSB_STATS})

    ar13_121 = get(NTSB_AR[("2013", "121")], "ntsb_ar2013_part121.xls")
    ar13_135 = get(NTSB_AR[("2013", "135")], "ntsb_ar2013_part135.xls")
    ar12_121 = get(NTSB_AR[("2012", "121")], "ntsb_ar2012_part121.xlsx")
    a13h, a13d = ar_sheet(ar13_121, "Part121_FlightHours"), ar_sheet(ar13_121, "Part121_Departures")
    a12h, a12d = ar_sheet(ar12_121, "Part121_FlightHours"), ar_sheet(ar12_121, "Part121_Departures")
    s13sched = ar_sheet(ar13_135, "Part135_Scheduled_FlightHours")
    s13fw = ar_sheet(ar13_135, "Part135_NonSched_FlightHours", col=2)
    rows.append({"year": 2004, "category": "airliner", "flight_hours": a13h[2004], "departures": a13d[2004],
                 "source": "NTSB Annual Review 2013 Part121 workbook sheets Part121_FlightHours + Part121_Departures",
                 "source_url": NTSB_AR[("2013", "121")]})
    rows.append({"year": 2003, "category": "airliner", "flight_hours": a12h[2003], "departures": a12d[2003],
                 "source": "NTSB Annual Review 2012 Part121 workbook sheets Part121_FlightHours + Part121_Departures",
                 "source_url": NTSB_AR[("2012", "121")]})
    rows.append({"year": 2004, "category": "charter", "flight_hours": s13sched[2004] + s13fw[2004], "departures": None,
                 "source": "NTSB Annual Review 2013 Part135 workbook sheets Part135_Scheduled_FlightHours + "
                           "Part135_NonSched_FlightHours (Fixed Wing)", "source_url": NTSB_AR[("2013", "135")]})

    # Older/overlapping editions, for the discrepancy report only.
    ar19_121 = get(NTSB_AR[("2019", "121")], "ntsb_ar2019_part121.xlsx")
    ar19_135 = get(NTSB_AR[("2019", "135")], "ntsb_ar2019_part135.xlsx")
    older = {
        "Part 121 hours (AR2013)": (a13h, {y: v["hours"] for y, v in t5.items()}),
        "Part 121 hours (AR2019)": (ar_sheet(ar19_121, "Part121_FlightHours", scale=1e5), {y: v["hours"] for y, v in t5.items()}),
        "Part 121 departures (AR2019)": (ar_sheet(ar19_121, "Part121_Departures", scale=1e5), {y: v["deps"] for y, v in t5.items()}),
        "Part 135 commuter hours (AR2013)": (s13sched, {y: v["hours"] for y, v in t8.items()}),
        "Part 135 commuter hours (AR2019)": (ar_sheet(ar19_135, "Part135_Scheduled_FlightHours", scale=1e5), {y: v["hours"] for y, v in t8.items()}),
        "On-demand fixed-wing hours (AR2013)": (s13fw, {y: v["hours"] for y, v in t17.items()}),
        "On-demand fixed-wing hours (AR2019)": (ar_sheet(ar19_135, "Part135_NonSched_FlightHours", col=2, scale=1e5), {y: v["hours"] for y, v in t17.items()}),
    }
    return rows, {"t17": t17, "t20": t20, "older": older}


def cross_check_ch1(survey: dict[int, dict]) -> list[str]:
    """Totals by type must match the latest Chapter I Table 1.3 (thousands of hours, 2013-2024)."""
    y0, url = FAA_CH1_LATEST
    df = read(get(url, f"faa_cy{y0}_ch1.xlsx"), "1.3")
    col0 = [("" if pd.isna(v) else str(v).strip()) for v in df.iloc[:, 0]]
    hdr_i = next(i for i, v in enumerate(col0) if v.upper().startswith("AIRCRAFT TYPE"))
    years = {int(num(v)): j for j, v in enumerate(df.iloc[hdr_i]) if num(v) is not None}
    lab = {"piston": "Piston: Total", "turboprop": "Turboprop: Total", "turbojet": "Turbojet: Total",
           "rotor": "Rotorcraft: Total"}
    msgs = []
    for k, label in lab.items():
        i = col0.index(label)
        for y, j in years.items():
            if y not in survey:
                continue
            ch1 = num(df.iat[i, j]) * 1000
            ours = survey[y]["tot"][k]
            rel = abs(ch1 - ours) / ours
            # 2015 is published rounded to 0.1 thousand-ish in the latest edition
            assert rel < 0.002, f"{y} {k}: Table 3.2 total {ours:.0f} vs Ch1 {y0} Table 1.3 {ch1:.0f}"
            if abs(ch1 - ours) > 2:
                msgs.append(f"{y} {k}: Table 3.2 {ours:.0f} vs Ch1 {y0} Table 1.3 {ch1:.0f} (rounded in Ch1)")
    return msgs


def main() -> int:
    survey = {}
    rows: list[dict] = []
    for y in sorted(FAA_CH3):
        r, info = survey_rows(y)
        rows += r
        survey[y] = info
    nrows, ninfo = ntsb_rows()
    rows += nrows

    # Cross-checks: survey Part 135 fixed-wing / rotorcraft hours vs NTSB Tables 17 / 20.
    print("survey Part 135 vs NTSB on-demand tables (max abs diff, hours):")
    d17 = max(abs(survey[y]["fw135"] - v["hours"]) for y, v in ninfo["t17"].items() if v["hours"] and y in survey)
    d20 = max(abs(survey[y]["rot135"] - v["hours"]) for y, v in ninfo["t20"].items() if v["hours"] and y in survey)
    print(f"  fixed-wing (Table 17): {d17:.0f}   rotorcraft (Table 20): {d20:.0f}")
    for m in cross_check_ch1(survey):
        print("  ", m)
    print("older NTSB editions that differ from the 2005-2024 statistics workbook (>0.1%):")
    for name, (old, new) in ninfo["older"].items():
        for y in sorted(set(old) & set(new)):
            if new[y] and abs(old[y] - new[y]) / new[y] > 0.001:
                print(f"   {name} {y}: {old[y]:,.0f} vs {new[y]:,.0f}")

    df = pd.DataFrame(rows)
    tr = pd.read_csv(paths.MANUAL / "exposure_transcribed.csv")
    clash = df.merge(tr, on=["year", "category"])
    assert clash.empty, f"transcribed rows overlap extracted rows: {clash[['year', 'category']].values.tolist()}"
    df = pd.concat([df, tr], ignore_index=True)
    df["flight_hours"] = df["flight_hours"].astype(float).round().astype("Int64")
    df["departures"] = pd.to_numeric(df["departures"]).round().astype("Int64")
    df = df[COLUMNS].sort_values(["category", "year"]).reset_index(drop=True)
    out = paths.MANUAL / "exposure_annual.csv"
    df.to_csv(out, index=False)
    load_exposure(out)  # validates columns, categories, positivity, duplicates
    for cat, g in df.groupby("category"):
        ys = sorted(g["year"])
        missing = sorted(set(range(ys[0], ys[-1] + 1)) - set(ys))
        print(f"{cat:11s} {ys[0]}-{ys[-1]} n={len(ys)} missing={missing}")
    print(f"wrote {out} ({len(df)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
