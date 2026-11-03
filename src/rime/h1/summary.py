"""Plain-language summary of the H1 results (results/h1/summary.md)."""
import math

import pandas as pd

NAMES = {"airliner": "airliner", "charter": "charter", "ga_piston": "private piston-plane",
         "ga_turbine": "private turbine-plane", "helicopter": "helicopter"}
PHASE_NAMES = {"el_nino": "El Niño", "la_nina": "La Niña", "super_el_nino": "super El Niño"}
LIMITATIONS = """- Flight-hour exposure is annual and national. The H1-N design compares months within the same year, so exposure errors can't bias it, but regional traffic isn't observed.
- The H1-R power figures assumed the tier's share of events (0.40, or a pessimistic 0.20); the shares weren't measured from the data.
- The power simulation assumed flat seasonality and Poisson month noise around year effects. That simplifies the fitted models.
- Counts are aircraft involvements, so a midair collision counts once per aircraft. "Fatal" is the event's highest injury.
- NTSB records from 2025 on are excluded because the cases are still being entered. Primary periods start in 1997 (airliners) or 2004 (all other types), after breaks in how flight hours were defined."""


def _pct(x: float) -> int:
    return round(abs(x - 1) * 100)


def _change(rr: float, lo: float, hi: float) -> str:
    word = "more" if rr >= 1 else "fewer"
    a, b = sorted((_pct(lo), _pct(hi))) if (lo - 1) * (hi - 1) > 0 else (None, None)
    ci = f"95% CI {a}–{b}%" if a is not None else f"95% CI {lo:.2f}–{hi:.2f}×"
    return f"{_pct(rr)}% {word} ({ci})"


def _range(lo: float, hi: float) -> str:
    f = lambda x: f"{'+' if x >= 1 else '−'}{_pct(x)}%"
    return f"{f(lo)} to {f(hi)}"


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def _sentence(r) -> str:
    who, when = NAMES.get(r.category, r.category), PHASE_NAMES.get(r.phase, r.phase)
    if r.status != "ok":
        return f"- {r.test}: could not be estimated (counted as p = 1)."
    excludes_one = r.ci_lo > 1 or r.ci_hi < 1
    if r.family == "H1-R":
        tier = r.test.split(" share")[0].split("ga_piston ")[-1]
        subject = _cap(f"the {tier}'s share of weather-involved {who} accidents in {when} winters")
        odds = lambda: _change(r.rr, r.ci_lo, r.ci_hi).replace("more", "higher").replace("fewer", "lower")
        if r.reject:
            return f"- {subject}: odds {odds()}, as predicted."
        if r.ci_hi < 1:
            return (f"- {subject}: opposite to the predicted direction, odds {odds()}. "
                    "The one-sided confirmatory test can't be significant in this direction; treat it as exploratory.")
        return f"- {subject}: no detectable relationship; the data rule out odds changes outside {_range(r.ci_lo, r.ci_hi)}."
    if r.reject:
        return f"- {when} months had {_change(r.rr, r.ci_lo, r.ci_hi)} weather-involved {who} accidents than neutral months."
    if excludes_one:
        return (f"- {_cap(who)}, {when}: nominally {_change(r.rr, r.ci_lo, r.ci_hi)} weather-involved accidents "
                f"(unadjusted p = {r.p:.3f}), but not significant after correcting for multiple tests "
                f"(Holm p = {r.p_holm:.2f}). Exploratory evidence only.")
    return (f"- {_cap(who)}, {when}: no detectable relationship; the data rule out effects "
            f"outside {_range(r.ci_lo, r.ci_hi)}.")


def _table(df: pd.DataFrame, cols: list[str]) -> str:
    if df.empty:
        return "_none_"
    fmt = lambda v: f"{v:.3g}" if isinstance(v, float) and not math.isnan(v) else ("" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v))
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(fmt(getattr(r, c)) for c in cols) + " |" for r in df.itertuples(index=False)]
    return "\n".join(lines)


def render_summary(conf: pd.DataFrame, nc: pd.DataFrame, sens: pd.DataFrame, meta: dict) -> str:
    parts = ["# rime H1 results: ENSO and weather-involved accident rates",
             f"Pre-registration: tag `prereg-v1` (`{meta.get('prereg_sha', '?')[:12]}`). Run: {meta.get('run_at_utc', '?')}."]
    parts.append("## Short answer")
    for fam in ("H1-N", "H1-R"):
        f = conf[conf["family"] == fam]
        if f.empty:
            continue
        n_rej = int(f["reject"].fillna(False).astype(bool).sum())
        parts.append(f"**{fam}:** {n_rej} of {len(f)} tests significant after Holm correction.")
        parts.append("\n".join(_sentence(r) for r in f.itertuples(index=False)))
    parts.append("## Every confirmatory test")
    parts.append(_table(conf, ["family", "test", "rr", "ci_lo", "ci_hi", "p", "p_holm", "reject", "n_events", "status", "model"]))
    parts.append("## Negative control (non-weather accidents, same models)")
    parts.append(_table(nc, ["test", "rr", "ci_lo", "ci_hi", "p", "p_holm", "reject", "n_events", "status"]))
    flagged = nc[(nc["family"] == "NC") & nc["reject"].fillna(False).astype(bool)] if not nc.empty else nc
    if len(flagged):
        for r in flagged.itertuples(index=False):
            parts.append(f"ENSO also shifts non-weather accidents for {NAMES.get(r.category, r.category)} "
                         f"({PHASE_NAMES.get(r.phase, r.phase)}), so the H1-N result for that category "
                         "may reflect something other than weather.")
    else:
        parts.append("No negative-control test was significant: ENSO phase doesn't shift non-weather accidents, as expected.")
    parts.append("## Sensitivity analyses (pre-specified, not confirmatory)")
    parts.append(_table(sens, ["sensitivity", "category", "phase", "rr", "ci_lo", "ci_hi", "p", "n_events", "status", "model"]))
    parts.append("## Limitations")
    parts.append(LIMITATIONS)
    return "\n\n".join(parts) + "\n"
