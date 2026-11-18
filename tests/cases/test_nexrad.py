from datetime import datetime

import numpy as np
import pandas as pd
import pytest

LAT_E = np.array([26.0, 26.5, 27.0])
LON_E = np.array([-81.0, -80.5, -80.0])


def _pts(rows):
    return pd.DataFrame(rows, columns=["lat", "lon", "height_m", "dbz"])


def test_grid_products_basic():
    from rime.cases.nexrad import grid_products
    g = grid_products(_pts([(26.2, -80.8, 5000, 30.0), (26.3, -80.7, 12000, 20.0)]), LAT_E, LON_E)
    c = g.isel(lat=0, lon=0)
    assert float(c.composite_dbz) == 30.0
    assert float(c.echo_top_km) == 12.0
    assert np.isnan(float(c.cruise_max_dbz))


def test_weak_echo_does_not_set_top_and_empty_cells_nan():
    from rime.cases.nexrad import grid_products
    g = grid_products(_pts([(26.2, -80.8, 13000, 10.0), (26.2, -80.8, 10000, 25.0)]), LAT_E, LON_E)
    c = g.isel(lat=0, lon=0)
    assert float(c.echo_top_km) == 10.0 and float(c.cruise_max_dbz) == 25.0
    e = g.isel(lat=1, lon=1)
    assert np.isnan(float(e.composite_dbz)) and np.isnan(float(e.echo_top_km))


@pytest.mark.slow
def test_list_volumes_kamx():
    from rime.cases.nexrad import list_volumes
    keys = list_volumes("KAMX", datetime(2026, 11, 1, 17, 35), datetime(2026, 11, 1, 17, 57))
    assert any(k.endswith("KAMX20261101_174548_V06") for k in keys)
    assert not any(k.endswith("_MDM") for k in keys)


def test_fill_codes_masked():
    from rime.cases.nexrad import valid_dbz
    v = valid_dbz(np.array([-33.0, -32.5, -32.0, 5.0, np.nan]))
    assert v.tolist() == [False, False, True, True, False]


@pytest.mark.slow
def test_real_volume_has_no_fill_values():
    from rime import paths
    from rime.cases.nexrad import volume_points
    f = paths.RAW / "cases" / "KAMX20261101_174548_V06"
    if not f.exists():
        pytest.skip("volume not cached")
    p = volume_points(f)
    assert p.dbz.min() >= -32.0 and len(p) < 6_000_000
