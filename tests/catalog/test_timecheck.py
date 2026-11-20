import numpy as np
import pandas as pd


def test_equinox_noon_overhead():
    from rime.catalog.timecheck import solar_elevation_deg
    e = solar_elevation_deg(0.0, 0.0, pd.Timestamp("2020-03-20 12:00"))
    assert 88 <= float(e) <= 90


def test_midnight_below_horizon():
    from rime.catalog.timecheck import solar_elevation_deg
    assert float(solar_elevation_deg(40.0, 0.0, pd.Timestamp("2020-06-21 00:00"))) < -20


def test_kobe_morning():
    from rime.catalog.timecheck import solar_elevation_deg
    assert 20 < float(solar_elevation_deg(34.14, -118.70, pd.Timestamp("2020-01-26 17:45"))) < 40


def test_nan_lat():
    from rime.catalog.timecheck import solar_elevation_deg
    assert np.isnan(float(solar_elevation_deg(np.nan, -100.0, pd.Timestamp("2020-01-01 12:00"))))


def test_vectorized_alaska_winter_finite():
    from rime.catalog.timecheck import solar_elevation_deg
    t = pd.to_datetime(["2020-12-21 21:00", "2020-12-21 09:00"])
    e = solar_elevation_deg(np.array([64.8, 64.8]), np.array([-147.7, -147.7]), t)
    assert np.isfinite(e).all() and e[1] < e[0]


def test_daynight_mismatch_rules():
    from rime.catalog.timecheck import daynight_mismatch
    elev = np.array([-10, -3, 20, 20, -10])
    cond = np.array(["DAYL", "DAYL", "NITE", "DUSK", None], dtype=object)
    assert daynight_mismatch(elev, cond).tolist() == [True, False, True, False, False]
