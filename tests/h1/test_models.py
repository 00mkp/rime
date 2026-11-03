import numpy as np
import pandas as pd


def _panel(rr=1.5, years=20, seed=0, mean=20.0):
    rng = np.random.default_rng(seed)
    rows = []
    for y in range(2000, 2000 + years):
        ye = rng.gamma(50, 1 / 50)
        for m in range(1, 13):
            k = (y * 12 + m) % 30
            phase = "el_nino" if k < 9 else ("la_nina" if k < 18 else "neutral")
            mu = mean * ye * (rr if phase == "el_nino" else 1.0)
            rows.append((y, m, phase, rng.poisson(mu)))
    return pd.DataFrame(rows, columns=["year", "month", "phase", "count"])


def test_fit_h1n_recovers_rr():
    from rime.h1.models import fit_h1n
    eff = fit_h1n(_panel(1.5))
    el, la = eff["el_nino"], eff["la_nina"]
    assert el.status == "ok"
    assert el.ci_lo <= el.rr <= el.ci_hi
    assert el.ci_lo > 1.2 and el.ci_hi < 1.8
    assert la.ci_lo < 1 < la.ci_hi


def test_fit_h1n_null_p_not_tiny():
    from rime.h1.models import fit_h1n
    eff = fit_h1n(_panel(1.0, seed=3))
    assert eff["el_nino"].p > 0.001 and eff["la_nina"].p > 0.001


def test_fit_h1n_not_estimable_when_no_events():
    from rime.h1.models import fit_h1n
    p = _panel(1.0)
    p["count"] = 0
    eff = fit_h1n(p)
    assert eff["el_nino"].status == "not_estimable" and eff["el_nino"].p == 1.0


def _tier(shift, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(2000, 2020):
        phase = ["el_nino", "la_nina", "neutral"][s % 3]
        share = 0.4 * (shift if phase == "el_nino" else 1.0)
        for m in (11, 12, 1, 2, 3):
            n = rng.poisson(20)
            t = rng.binomial(n, min(share, 0.95))
            rows.append((s, m, s, phase, t, n - t))
    return pd.DataFrame(rows, columns=["year", "month", "season", "phase", "tier_count", "rest_count"])


def test_fit_h1r_one_sided():
    from rime.h1.models import fit_h1r
    assert fit_h1r(_tier(1.5), "el_nino").p < 0.01
    assert fit_h1r(_tier(0.6), "el_nino").p > 0.5


def test_holm_adjusts():
    from rime.h1.models import Effect, holm
    e = {"a": Effect(1, 1, 1, 0.01, 1, "ok"), "b": Effect(1, 1, 1, 0.04, 1, "ok")}
    out = holm(e)
    assert np.isclose(out["a"][0], 0.02) and np.isclose(out["b"][0], 0.04)
    assert out["a"][1] and out["b"][1]


def test_fit_h1n_uses_nb_when_overdispersed():
    import numpy as np
    from rime.h1.models import fit_h1n
    rng = np.random.default_rng(5)
    p = _panel(1.0, seed=5)
    p["count"] = rng.negative_binomial(2, 2 / (2 + 20), len(p))  # alpha = 0.5
    assert fit_h1n(p)["el_nino"].model == "nb"
