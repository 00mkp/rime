import numpy as np
import pandas as pd

YEARS = list(range(1990, 2025))


def test_trend_detects_slope():
    from rime.h2.models import trend_test
    rng = np.random.default_rng(0)
    idx = 0.2 + 0.01 * (np.array(YEARS) - 1990) + rng.normal(0, 0.01, len(YEARS))
    e = trend_test(YEARS, idx)
    assert e.p < 0.01 and e.ci_lo < 0.1 < e.ci_hi


def _link_data(rr=1.3, seed=1, n_years=35, base=40):
    rng = np.random.default_rng(seed)
    years = pd.Index(range(1990, 1990 + n_years))
    index = pd.Series(rng.normal(0.3, 0.05, n_years), index=years)
    hours = pd.Series(1e7, index=years)
    z = (index - index.mean()) / index.std()
    counts = pd.Series(rng.poisson(base * rr ** z), index=years)
    return counts, index, hours


def test_link_recovers_effect():
    from rime.h2.models import link_test
    e = link_test(*_link_data(1.3), break_2008=False)
    assert e.ci_lo < 1.3 < e.ci_hi and e.p < 0.05


def test_link_break_indicator_included():
    from rime.h2.models import link_model
    res = link_model(*_link_data(), break_2008=True)
    assert "post2008" in res.model.exog_names


def _inputs(n_events_turb_ga=12):
    years = list(range(2004, 2025))
    rows = []
    for y in years:
        for c in ("airliner", "charter", "ga_piston", "ga_turbine", "helicopter"):
            for hz in ("icing", "turbulence", "convective", "h3"):
                n = 5
                if (c, hz) == ("ga_piston", "turbulence"):
                    n = 0
                rows.append((y, c, hz, n))
    hc = pd.DataFrame(rows, columns=["year", "category", "hazard", "count"])
    hc.loc[(hc.category == "ga_piston") & (hc.hazard == "turbulence") & (hc.year == 2010), "count"] = n_events_turb_ga
    annual = pd.DataFrame({"year": YEARS, "icing": 0.2, "turbulence": 0.1, "convective": 0.05, "hiwc": 0.01,
                           "n_months": 12, "complete": True})
    rng = np.random.default_rng(3)
    for c in ("icing", "turbulence", "convective", "hiwc"):
        annual[c] = annual[c] + rng.normal(0, 0.005, len(YEARS))
    exp = pd.DataFrame([(y, c, 1e6, None, "s", "u") for y in YEARS
                        for c in ("airliner", "charter", "ga_piston", "ga_turbine", "helicopter")],
                       columns=["year", "category", "flight_hours", "departures", "source", "source_url"])
    breaks = {"icing": False, "turbulence": False, "convective": False}
    return hc, annual, exp, breaks


def test_descriptive_below_minimum():
    from rime.h2.run import build_h2_rows
    rows = build_h2_rows(*_inputs(12))
    r = rows[(rows.family == "H2b") & (rows.category == "ga_piston") & (rows.hazard == "turbulence")].iloc[0]
    assert r.status == "descriptive" and r.n == 12 and pd.isna(r.p_holm)
    tested = rows[(rows.family == "H2b") & (rows.status == "ok")]
    assert len(tested) == 14 and tested.p_holm.notna().all()
    assert set(rows.family) == {"H2a", "H2b", "H3a", "H3b"}


def test_run_h2_reports_missing_indices(tmp_path, monkeypatch, capsys):
    from rime import paths
    from rime.h2.run import run_h2
    monkeypatch.setattr(paths, "PROCESSED", tmp_path / "processed")
    monkeypatch.setattr(paths, "RESULTS", tmp_path / "results")
    run_h2()
    assert "ERA5 indices missing" in capsys.readouterr().out
    assert not (tmp_path / "results" / "h2").exists()


def test_h2a_limited_to_1990_2024():
    from rime.h2.run import build_h2_rows
    hc, annual, exp, breaks = _inputs(40)
    extra = annual.iloc[[-1]].assign(year=2025)
    rows = build_h2_rows(hc, pd.concat([annual, extra]), exp, breaks)
    assert (rows.loc[rows.family == "H2a", "n"] == 35).all()


def test_sensitivity_post2008_indicator_rows():
    from rime.h2.run import build_h2_sensitivity
    s = build_h2_sensitivity(*_inputs(40))
    assert set(s.sensitivity) == {"post2008_indicator"}
    assert set(s.family) == {"H2b", "H3b"}


def test_link_degenerate_fit_not_estimable_not_infinite():
    import warnings
    from rime.h2.run import build_h2_rows
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        rows = build_h2_rows(*_inputs(40))  # ga_piston turbulence: all 40 events in one year
    r = rows[(rows.family == "H2b") & (rows.category == "ga_piston") & (rows.hazard == "turbulence")].iloc[0]
    assert r.status == "not_estimable" or (np.isfinite(r.estimate) and np.isfinite(r.ci_hi))
