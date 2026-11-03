import pandas as pd


def _ev(rows):
    cols = ["year", "month", "ev_type", "category", "region", "wx_involved", "fatal"]
    return pd.DataFrame(rows, columns=cols)


def _enso(months, el=(), sup=()):
    m = pd.date_range(months[0], months[1], freq="MS")
    return pd.DataFrame({
        "month": m,
        "phase": ["el_nino" if d.strftime("%Y-%m") in el else "neutral" for d in m],
        "super": [d.strftime("%Y-%m") in sup for d in m],
    })


def test_panel_zero_fills_missing_months():
    from rime.h1.panel import monthly_panel, phase_lookup
    ev = _ev([(2005, 1, "ACC", "ga_piston", "south", True, False)])
    p = monthly_panel(ev, phase_lookup(_enso(("2004-01", "2006-12"))), category="ga_piston", years=[2005])
    assert len(p) == 12
    assert p.set_index("month")["count"].to_dict() == {m: (1 if m == 1 else 0) for m in range(1, 13)}


def test_panel_outcome_filters():
    from rime.h1.panel import monthly_panel, phase_lookup
    ev = _ev([(2005, 3, "ACC", "ga_piston", "south", True, False),
              (2005, 3, "ACC", "ga_piston", "south", False, True),
              (2005, 3, "INC", "ga_piston", "south", True, False)])
    ph = phase_lookup(_enso(("2004-01", "2006-12")))
    get = lambda o: monthly_panel(ev, ph, category="ga_piston", years=[2005], outcome=o).set_index("month").loc[3, "count"]
    assert (get("wx"), get("non_wx"), get("fatal_wx")) == (1, 1, 0)


def test_panel_region_filter():
    from rime.h1.panel import SOUTHERN_TIER, monthly_panel, phase_lookup
    ev = _ev([(2005, 3, "ACC", "ga_piston", "southeast", True, False),
              (2005, 3, "ACC", "ga_piston", "northwest", True, False)])
    p = monthly_panel(ev, phase_lookup(_enso(("2004-01", "2006-12"))), category="ga_piston",
                      years=[2005], regions=SOUTHERN_TIER)
    assert p.set_index("month").loc[3, "count"] == 1


def test_phase_lag3_crosses_year():
    from rime.h1.panel import phase_lookup
    ph = phase_lookup(_enso(("2004-01", "2006-12"), el={"2004-10"}), lag=3).set_index(["year", "month"])
    assert ph.loc[(2005, 1), "phase"] == "el_nino"
    assert ph.loc[(2004, 10), "phase"] == "neutral"


def test_super_level_replaces_el_nino():
    from rime.h1.panel import phase_lookup
    e = _enso(("2004-01", "2004-12"), el={"2004-05", "2004-06"}, sup={"2004-05"})
    ph = phase_lookup(e, super_level=True).set_index(["year", "month"])
    assert ph.loc[(2004, 5), "phase"] == "super_el_nino"
    assert ph.loc[(2004, 6), "phase"] == "el_nino"


def test_tier_panel_winter_only_and_rest():
    from rime.h1.panel import SOUTHERN_TIER, phase_lookup, tier_panel
    rows = [(2005, 12, "ACC", "ga_piston", "southeast", True, False)] * 3
    rows += [(2005, 12, "ACC", "ga_piston", "northwest", True, False)] * 2
    rows += [(2005, 7, "ACC", "ga_piston", "southeast", True, False)]
    t = tier_panel(_ev(rows), phase_lookup(_enso(("2004-01", "2007-12"))), category="ga_piston",
                   years=[2005, 2006], tier=SOUTHERN_TIER).set_index(["year", "month"])
    assert (t.loc[(2005, 12), "tier_count"], t.loc[(2005, 12), "rest_count"]) == (3, 2)
    assert t.loc[(2005, 12), "season"] == 2005
    assert (2005, 7) not in t.index
    assert t.loc[(2006, 2), "season"] == 2005
