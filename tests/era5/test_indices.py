import numpy as np
import pandas as pd
import pytest
import xarray as xr

LAT = np.arange(40.0, 38.75, -0.25)   # 5 rows, descending like ERA5
LON = np.arange(-100.0, -98.75, 0.25)  # 5 cols
T1 = pd.to_datetime(["2005-01-01T00:00"])
R = 6_371_000.0


def _pl(values: dict, levels, times=T1):
    """values: level -> scalar or (lat, lon) array"""
    data = np.stack([np.broadcast_to(np.asarray(values[l], float), (len(LAT), len(LON))) for l in levels])
    return xr.DataArray(data[None].repeat(len(times), 0), dims=("valid_time", "pressure_level", "latitude", "longitude"),
                        coords={"valid_time": times, "pressure_level": levels, "latitude": LAT, "longitude": LON})


def _sl(value, times=T1):
    data = np.broadcast_to(np.asarray(value, float), (len(times), len(LAT), len(LON))).copy()
    return xr.DataArray(data, dims=("valid_time", "latitude", "longitude"),
                        coords={"valid_time": times, "latitude": LAT, "longitude": LON})


ICING = [850, 500, 400]


def test_icing_mask_requires_all_three():
    from rime.era5.indices import icing_mask
    ok = lambda t, r, c: float(icing_mask(_pl({l: t for l in ICING}, ICING), _pl({l: r for l in ICING}, ICING),
                                          _pl({l: c for l in ICING}, ICING)).isel(latitude=2, longitude=2).squeeze())
    assert ok(263, 90, 2e-5) == 1
    assert ok(263, 80, 2e-5) == 0
    assert ok(263, 90, 5e-6) == 0
    assert ok(250, 90, 2e-5) == 0
    assert ok(275, 90, 2e-5) == 0


def test_icing_any_level():
    from rime.era5.indices import icing_mask
    t = _pl({850: 280, 500: 263, 400: 245}, ICING)
    r = _pl({l: 90 for l in ICING}, ICING)
    c = _pl({l: 2e-5 for l in ICING}, ICING)
    assert float(icing_mask(t, r, c).isel(latitude=2, longitude=2).squeeze()) == 1


def _upper(a):
    y = R * np.deg2rad(LAT)[:, None] * np.ones(len(LON))[None, :]
    levels = [300, 250, 200]
    u = _pl({300: a * y, 250: a * y + 10, 200: a * y + 10}, levels)
    v = _pl({l: 0.0 for l in levels}, levels)
    z = _pl({300: 9160 * 9.80665, 250: 10360 * 9.80665, 200: 11780 * 9.80665}, levels)
    return u, v, z


def test_ellrod_known_value():
    from rime.era5.indices import ellrod_ti1
    ti = ellrod_ti1(*_upper(1e-4))
    expected = (10 / 1200) * 1e-4
    assert abs(float(ti.isel(latitude=2, longitude=2).squeeze()) / expected - 1) < 0.05
    assert np.isnan(ti.isel(latitude=0)).all() and np.isnan(ti.isel(longitude=-1)).all()


def test_turbulence_threshold():
    from rime.era5.indices import turbulence_mask
    assert float(turbulence_mask(*_upper(1e-4)).isel(latitude=2, longitude=2).squeeze()) == 1   # 8.3e-7
    assert float(turbulence_mask(*_upper(0.9e-4)).isel(latitude=2, longitude=2).squeeze()) == 0  # 7.5e-7


def test_cp6_sums_window_and_needs_history():
    from rime.era5.indices import cp_6h
    times = pd.date_range("2005-01-01T00:00", periods=8, freq="h")
    out = cp_6h(_sl(0.0002, times))
    assert np.isclose(float(out.sel(valid_time=times[5]).isel(latitude=0, longitude=0).squeeze()), 0.0012)
    assert np.isnan(float(out.sel(valid_time=times[3]).isel(latitude=0, longitude=0).squeeze()))


def test_convective_mask():
    from rime.era5.indices import convective_mask
    assert float(convective_mask(_sl(1200), _sl(0.0011)).isel(latitude=0, longitude=0).squeeze()) == 1
    assert float(convective_mask(_sl(900), _sl(0.0011)).isel(latitude=0, longitude=0).squeeze()) == 0
    assert float(convective_mask(_sl(1200), _sl(0.0009)).isel(latitude=0, longitude=0).squeeze()) == 0


def test_hiwc_mask():
    from rime.era5.indices import hiwc_mask
    hi = _pl({300: 0.0, 250: 6e-5}, [300, 250])
    assert float(hiwc_mask(_sl(1600), hi).isel(latitude=0, longitude=0).squeeze()) == 1
    lo = _pl({300: 0.0, 250: 0.0, 400: 6e-5}, [400, 300, 250])
    assert float(hiwc_mask(_sl(1600), lo).isel(latitude=0, longitude=0).squeeze()) == 0
    assert float(hiwc_mask(_sl(1400), hi).isel(latitude=0, longitude=0).squeeze()) == 0


def test_conus_share_ignores_nan():
    from rime.era5.indices import conus_share
    m = np.zeros((1, len(LAT), len(LON)))
    m[0, 0, 0], m[0, 0, 1] = 1, np.nan
    mask = xr.DataArray(m, dims=("valid_time", "latitude", "longitude"),
                        coords={"valid_time": T1, "latitude": LAT, "longitude": LON})
    conus = xr.zeros_like(mask.isel(valid_time=0), dtype=bool)
    conus[0, 0:4] = True
    assert np.isclose(float(conus_share(mask, conus).isel(valid_time=0)), 1 / 3)


@pytest.mark.slow
def test_conus_mask_excludes_ocean_and_canada():
    from rime.era5.mask import conus_mask
    lat = np.arange(50.0, 23.75, -0.25)
    lon = np.arange(-125.0, -65.75, 0.25)
    m = conus_mask(lat, lon, cache=False)
    at = lambda la, lo: bool(m.sel(latitude=la, longitude=lo))
    assert at(39.0, -98.0) and at(25.75, -80.5)
    assert not at(35.0, -70.0)
    assert not at(49.75, -100.0)
