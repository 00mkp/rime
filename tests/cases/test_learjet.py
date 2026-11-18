import numpy as np
import xarray as xr

CENTER = (26.6295, -80.117)


def _grid():
    lat = np.arange(26.0, 27.3, 0.01)
    lon = np.arange(-80.8, -79.4, 0.01)
    shape = (len(lat), len(lon))
    ds = xr.Dataset({v: (("lat", "lon"), np.full(shape, np.nan)) for v in ("composite_dbz", "echo_top_km", "cruise_max_dbz")},
                    coords={"lat": lat, "lon": lon})
    return ds


def test_ring_stats_picks_echo_top_by_distance():
    from rime.cases.learjet import ring_stats
    ds = _grid()
    i = int(np.argmin(abs(ds.lat.values - (CENTER[0] + 0.18))))  # ~20 km north
    j = int(np.argmin(abs(ds.lon.values - CENTER[1])))
    ds["echo_top_km"][i, j] = 12.0
    ds["composite_dbz"][i, j] = 45.0
    s = ring_stats(ds, CENTER).set_index("region")
    assert np.isnan(s.loc["within_15km", "max_echo_top_km"])
    assert s.loc["within_30km", "max_echo_top_km"] == 12.0
    assert s.loc["within_30km", "area_echo_top_ge_10_7km_km2"] > 0


def test_sector_excludes_due_east():
    from rime.cases.learjet import ring_stats
    ds = _grid()
    i = int(np.argmin(abs(ds.lat.values - CENTER[0])))
    j = int(np.argmin(abs(ds.lon.values - (CENTER[1] + 0.3))))  # ~30 km east
    ds["echo_top_km"][i, j] = 13.0
    s = ring_stats(ds, CENTER).set_index("region")
    assert np.isnan(s.loc["approach_sector_60km", "max_echo_top_km"])
    assert s.loc["within_60km", "max_echo_top_km"] == 13.0


def test_goes_stats_min_bt():
    from rime.cases.learjet import goes_stats
    lat, lon = np.meshgrid(np.arange(26.0, 27.3, 0.02), np.arange(-80.8, -79.4, 0.02), indexing="ij")
    bt = np.full(lat.shape, 290.0)
    k = np.unravel_index(np.argmin((lat - CENTER[0]) ** 2 + (lon - CENTER[1]) ** 2), lat.shape)
    bt[k] = 200.0
    ds = xr.Dataset({"bt_k": (("y", "x"), bt), "lat": (("y", "x"), lat), "lon": (("y", "x"), lon)})
    s = goes_stats(ds, CENTER).set_index("region")
    assert abs(s.loc["within_15km", "min_bt_c"] - (-73.15)) < 0.01
    assert s.loc["within_15km", "area_bt_le_minus60c_km2"] > 0


def _facts():
    import pandas as pd
    from rime.cases.learjet import render_facts
    regions = ["within_15km", "within_30km", "within_60km", "approach_sector_60km"]
    radar = pd.DataFrame({"region": regions, "max_composite_dbz": 58.5, "max_echo_top_km": 12.4,
                          "area_echo_top_ge_10_7km_km2": 70.0, "max_cruise_dbz": 39.0,
                          "volume_start_utc": "2026-11-01T17:45:48"})
    sat = pd.DataFrame({"region": regions, "min_bt_c": -69.2, "area_bt_le_minus60c_km2": 712.0,
                        "scan_start_utc": "2026-11-01T17:46:17"})
    sweeps = pd.DataFrame({"elevation": [4.0, 5.1, 6.4], "start_utc": ["17:49:09", "17:49:22", "17:49:36"],
                           "end_utc": ["17:49:21", "17:49:35", "17:49:49"], "height_km_at_range": [8.9, 11.2, 13.8]})
    return render_facts(radar, sat, sweeps)


def test_facts_has_no_mechanism_speculation():
    md = _facts().lower()
    assert "ice-crystal" not in md and "ice crystal" not in md
    assert "ntsb has not characterized the icing further" in md


def test_facts_states_radar_limits_and_sweep_times():
    md = _facts()
    assert "~2 km" in md and "17:49:09" in md and "17:49:49" in md
    assert "well sampled" not in md


def test_facts_quotes_ntsb_with_link_and_uses_unicode_minus():
    md = _facts()
    assert "some indication that the aircraft was breaking before impact" in md
    assert "wptv.com" in md
    assert "-54.3" not in md and "-69.2" not in md and "−69.2" in md
    assert "brightness temperature" in md and "pressure altitude" in md
