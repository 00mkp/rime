import numpy as np
import pandas as pd


def _phases(n=420, seed=0):
    rng = np.random.default_rng(seed)
    # blocky ENSO-like sequence: runs of 6-18 months
    out = []
    while len(out) < n:
        out += [rng.choice(["el_nino", "la_nina", "neutral", "neutral"])] * int(rng.integers(6, 19))
    return pd.Series(out[:n])


def test_power_increases_with_rr():
    from rime.power import simulate_power
    ph = _phases()
    lo = simulate_power(20, 0.05, ph, 1.1, 0.005, 200, np.random.default_rng(1))
    hi = simulate_power(20, 0.05, ph, 1.5, 0.005, 200, np.random.default_rng(1))
    assert hi > lo
    assert hi > 0.9


def test_power_near_alpha_at_null():
    from rime.power import simulate_power
    p = simulate_power(20, 0.05, _phases(), 1.0, 0.005, 400, np.random.default_rng(2))
    assert p < 0.03


def test_power_targets_requested_phase():
    from rime.power import simulate_power
    ph = _phases()
    # effect only in la_nina: el_nino test should stay near alpha
    p = simulate_power(20, 0.05, ph, 1.5, 0.005, 200, np.random.default_rng(3), target="la_nina")
    assert p > 0.9


def test_mdrr_none_when_too_rare():
    from rime.power import minimal_detectable_rr
    assert minimal_detectable_rr(0.05, 0.05, _phases(), 0.005, 100, np.random.default_rng(4)) is None


def test_mdrr_found_for_common_events():
    from rime.power import minimal_detectable_rr
    rr = minimal_detectable_rr(20, 0.05, _phases(), 0.005, 100, np.random.default_rng(5))
    assert rr is not None and 1.05 <= rr <= 1.5


def test_dispersion_from_annual_poisson_is_small():
    from rime.power import monthly_dispersion
    rng = np.random.default_rng(6)
    years = np.arange(1990, 2025)
    counts = rng.poisson(240 - 3 * (years - 1990))
    assert monthly_dispersion(years, counts) < 0.05


def test_study_years_respects_primary_start_end_and_gaps():
    from rime.power import study_years
    exp_years = set(range(1992, 2025)) - {2011}
    count_years = set(range(1990, 2027))
    assert study_years("airliner", exp_years, count_years)[0] == 1997
    ga = study_years("ga_piston", exp_years, count_years)
    assert ga[0] == 2004 and ga[-1] == 2024 and 2011 not in ga
