import numpy as np


def test_haversine_one_degree_equator():
    from rime.cases.geo import haversine_km
    assert abs(haversine_km(0, 0, 0, 1) - 111.19) < 0.05


def test_bearing_toward_austin_is_wnw():
    from rime.cases.geo import bearing_deg
    assert 285 < bearing_deg(26.63, -80.12, 30.1945, -97.6699) < 300


def test_beam_height_half_degree_100km():
    from rime.cases.geo import beam_height_m
    assert abs(beam_height_m(100e3, 0.5, 0.0) - 1460) < 50


def test_gate_latlon_east():
    from rime.cases.geo import gate_latlon
    lat, lon = gate_latlon(25.0, -80.0, 50e3, 90.0, 0.0)
    assert abs(lat - 25.0) < 0.01 and abs(lon - (-79.504)) < 0.01


def test_in_sector_wraps():
    from rime.cases.geo import in_sector
    assert in_sector(355, 340, 20) and not in_sector(30, 340, 20)
    assert np.array_equal(in_sector(np.array([260, 200]), 250, 330), [True, False])
