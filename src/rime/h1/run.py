"""`rime h1`: the locked H1 tests, negative control, and sensitivities (prereg/hypotheses.md)."""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from rime import paths
from rime.cli import register
from rime.exposure import load_exposure
from rime.h1.models import Effect, fit_h1n, fit_h1n_original, fit_h1r, holm
from rime.h1.panel import NORTHERN_TIER, SOUTHERN_TIER, monthly_panel, phase_lookup, tier_panel
from rime.ntsb.classify import CATEGORIES
from rime.power import END_YEAR, study_years

PHASES = ("el_nino", "la_nina")
EXPLORATORY = {("charter", "la_nina")}  # MDRR > 2.0 in the locked power table
FULL_START = {"airliner": 1992, "charter": 2004, "ga_piston": 1999, "ga_turbine": 1999, "helicopter": 1999}
H1R = [("H1-Ra", SOUTHERN_TIER, "el_nino", "southern tier"),
       ("H1-Rb", NORTHERN_TIER, "la_nina", "northern tier")]


def require_prereg_lock(repo: Path = paths.ROOT) -> str:
    r = subprocess.run(["git", "rev-list", "-n", "1", "prereg-v1"], cwd=repo,
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit("prereg-v1 tag not found: H1 outcomes may not be computed before "
                         "the pre-registration is locked")
    return r.stdout.strip()


def h1n_tests() -> list[tuple[str, str]]:
    return [(c, p) for c in CATEGORIES for p in PHASES if (c, p) not in EXPLORATORY]


def _row(e: Effect, **keys) -> dict:
    return {**keys, "rr": e.rr, "ci_lo": e.ci_lo, "ci_hi": e.ci_hi, "p": e.p,
            "n_events": e.n_events, "status": e.status, "model": e.model}


def _family(fits: dict[tuple[str, str], Effect], family: str) -> list[dict]:
    """Holm over the confirmatory pairs; exploratory pairs listed without adjustment."""
    conf = {k: v for k, v in fits.items() if k not in EXPLORATORY}
    adj = holm({f"{c}|{p}": e for (c, p), e in conf.items()})
    rows = []
    for (c, p), e in fits.items():
        pa, rej = adj.get(f"{c}|{p}", (None, None))
        rows.append(_row(e, family=family if (c, p) in conf else f"{family} (exploratory)",
                         test=f"{c} {p}", category=c, phase=p, p_holm=pa, reject=rej))
    return rows


def run_h1() -> None:
    sha = require_prereg_lock()
    events = pd.read_parquet(paths.PROCESSED / "events_aircraft.parquet")
    enso = pd.read_parquet(paths.PROCESSED / "enso_monthly.parquet")
    exposure = load_exposure()
    ph0, ph3, phs = phase_lookup(enso), phase_lookup(enso, lag=3), phase_lookup(enso, super_level=True)
    regions_no_akhi = frozenset(set(events["region"]) - {"alaska", "hawaii"})

    years, full_years, hours = {}, {}, {}
    for c in CATEGORIES:
        exp_c = exposure[exposure["category"] == c]
        cnt_years = events.loc[events["category"] == c, "year"].unique()
        years[c] = study_years(c, exp_c["year"], cnt_years)
        full_years[c] = sorted(y for y in set(exp_c["year"]) & set(cnt_years) if FULL_START[c] <= y <= END_YEAR)
        hours[c] = exp_c.set_index("year")["flight_hours"]

    def fits(outcome="wx", phases=ph0, yrs=years, regions=None, model=fit_h1n):
        out = {}
        for c in CATEGORIES:
            panel = monthly_panel(events, phases, category=c, years=yrs[c], outcome=outcome, regions=regions)
            res = model(panel) if model is fit_h1n else model(panel, hours[c])
            for p, e in res.items():
                out[(c, p)] = e
        return out

    conf = _family({k: v for k, v in fits().items() if k[1] in PHASES}, "H1-N")
    h1r = {}
    for name, tier, target, label in H1R:
        t = tier_panel(events, ph0, category="ga_piston", years=years["ga_piston"], tier=tier)
        h1r[name] = (fit_h1r(t, target), target, label)
    adj = holm({k: v[0] for k, v in h1r.items()})
    for name, (e, target, label) in h1r.items():
        conf.append(_row(e, family="H1-R", test=f"{name} ga_piston {label} share, {target} winters",
                         category="ga_piston", phase=target, p_holm=adj[name][0], reject=adj[name][1]))

    nc = _family({k: v for k, v in fits(outcome="non_wx").items() if k[1] in PHASES}, "NC")

    sens = []
    for name, kwargs in [("lag3", {"phases": ph3}), ("fatal_wx", {"outcome": "fatal_wx"}),
                         ("excl_ak_hi", {"regions": regions_no_akhi}), ("super_level", {"phases": phs}),
                         ("full_span", {"yrs": full_years}), ("original_model", {"model": fit_h1n_original})]:
        for (c, p), e in fits(**kwargs).items():
            sens.append(_row(e, sensitivity=name, category=c, phase=p))

    out = paths.RESULTS / "h1"
    out.mkdir(parents=True, exist_ok=True)
    conf_df, nc_df, sens_df = pd.DataFrame(conf), pd.DataFrame(nc), pd.DataFrame(sens)
    conf_df.to_csv(out / "confirmatory.csv", index=False)
    nc_df.to_csv(out / "negative_control.csv", index=False)
    sens_df.to_csv(out / "sensitivity.csv", index=False)
    versions = json.loads((paths.MANUAL / "data_versions.json").read_text())
    meta = {"prereg_sha": sha, "run_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "inputs": {k: versions[k]["sha256"] for k in ("avall.zip", "pre2008.zip") if k in versions},
            "periods": {c: f"{y[0]}-{y[-1]} ({len(y)} yrs)" for c, y in years.items()},
            "n_tests": {"H1-N": len(h1n_tests()), "H1-R": len(H1R)}}
    (out / "meta.json").write_text(json.dumps(meta, indent=2))
    _after_run(conf_df, nc_df, sens_df, meta)
    print(conf_df[["family", "test", "rr", "ci_lo", "ci_hi", "p_holm", "reject", "status"]].to_string(index=False))


def _after_run(conf, nc, sens, meta) -> None:
    """Hook for the summary writer (Task 4)."""


register("h1", run_h1, "run the locked H1 ENSO tests (requires the prereg-v1 tag)")
