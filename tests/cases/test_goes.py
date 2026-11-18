from datetime import datetime

import numpy as np
import pytest

PROJ = dict(perspective_point_height=35786023.0, semi_major_axis=6378137.0,
            semi_minor_axis=6356752.31414, longitude_of_projection_origin=-75.2)


def test_subsatellite_point():
    from rime.cases.goes import navigate
    lat, lon = navigate(np.array([0.0]), np.array([0.0]), **PROJ)
    assert abs(lat[0]) < 1e-9 and abs(lon[0] - (-75.2)) < 1e-9


def test_off_disk_is_nan():
    from rime.cases.goes import navigate
    lat, lon = navigate(np.array([0.2]), np.array([0.0]), **PROJ)
    assert np.isnan(lat[0]) and np.isnan(lon[0])


def test_known_point_roundtrip_latitude_sign():
    from rime.cases.goes import navigate
    lat, lon = navigate(np.array([-0.02]), np.array([0.07]), **PROJ)  # NW of sub-satellite point
    assert lat[0] > 0 and lon[0] < -75.2


@pytest.mark.slow
def test_real_scan_bt_range_near_impact():
    from rime.cases.goes import bt_latlon, fetch_scan, list_scans
    from rime.cases.geo import haversine_km
    key = [k for k in list_scans(datetime(2026, 11, 1, 17, 45), datetime(2026, 11, 1, 17, 47))][0]
    ds = bt_latlon(fetch_scan(key))
    near = haversine_km(26.6295, -80.117, ds.lat, ds.lon) < 30
    bt = ds.bt_k.where(near)
    assert 180 < float(bt.min()) and float(bt.max()) < 320
