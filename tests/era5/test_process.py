import numpy as np
import pandas as pd
import pytest
import xarray as xr

from synth import LAT, LON, SynthClient, write_month


@pytest.fixture
def tmp_paths(tmp_path, monkeypatch):
    from rime import paths
    monkeypatch.setattr(paths, "RAW", tmp_path / "raw")
    monkeypatch.setattr(paths, "PROCESSED", tmp_path / "processed")
    (tmp_path / "processed").mkdir()
    return tmp_path


def _conus():
    return xr.DataArray(np.ones((len(LAT), len(LON)), bool), dims=("latitude", "longitude"),
                        coords={"latitude": LAT, "longitude": LON})


def test_process_month_shares(tmp_path):
    from rime.era5.process import process_month
    files = write_month(tmp_path / "m", 2005, 2, icing_rows=1)
    out = process_month(2005, 2, files, _conus())
    assert len(out) == 28 * 4
    assert np.allclose(out["icing"], 0.25)
    assert set(out["time"].dt.hour) == {0, 6, 12, 18}


def test_cp_window_uses_previous_month(tmp_path):
    from rime.era5.process import process_month
    files = write_month(tmp_path / "m", 2005, 3, cp=0.0002, cape=1200.0)
    out = process_month(2005, 3, files, _conus()).set_index("time")
    assert out.loc[pd.Timestamp("2005-03-01T00:00"), "convective"] == 1.0


def test_process_month_without_previous_hours_is_nan_not_zero(tmp_path):
    from rime.era5.process import process_month
    files = write_month(tmp_path / "m", 2005, 3, skip=("sl_cp_prev",))
    files["sl_cp_prev"] = None
    out = process_month(2005, 3, files, _conus()).set_index("time")
    assert np.isnan(out.loc[pd.Timestamp("2005-03-01T00:00"), "convective"])


def test_run_month_records_failure_on_corrupt_file(tmp_paths):
    from rime.era5.download import load_manifest
    from rime.era5.process import run_month
    status = run_month(2005, 3, client=SynthClient(garbage=True), conus=_conus())
    assert status.startswith("failed:")
    assert load_manifest()["2005-03"]["status"].startswith("failed:")
    assert not (tmp_paths / "processed" / "era5_shares.parquet").exists()


def test_raw_deleted_after_success(tmp_paths):
    from rime.era5.download import load_manifest
    from rime.era5.process import run_month
    assert run_month(2005, 3, client=SynthClient(), conus=_conus()) == "done"
    assert load_manifest()["2005-03"]["status"] == "done"
    assert not (tmp_paths / "raw" / "era5" / "2005-03").exists()
    shares = pd.read_parquet(tmp_paths / "processed" / "era5_shares.parquet")
    assert len(shares) == 31 * 4


def test_annual_incomplete_year(tmp_paths):
    from rime.era5.process import annual_indices
    t = pd.date_range("1995-01-01", "1995-11-30T18:00", freq="6h")
    pd.DataFrame({"time": t, "icing": 0.1, "turbulence": 0.1, "convective": 0.1, "hiwc": 0.0}).to_parquet(
        tmp_paths / "processed" / "era5_shares.parquet", index=False)
    a = annual_indices().set_index("year")
    assert a.loc[1995, "n_months"] == 11 and not a.loc[1995, "complete"]


def test_era5_step_not_in_all():
    from rime import cli
    cli._load_steps()
    assert "era5" in cli._STEPS and "era5" not in cli.all_steps()


def test_short_month_fails_validation(tmp_path):
    from rime.era5.process import process_month, validate_month
    files = write_month(tmp_path / "m", 2005, 3)
    df = process_month(2005, 3, files, _conus()).iloc[:-4]
    with pytest.raises(ValueError, match="expected 124"):
        validate_month(2005, 3, df)


def test_cp_gap_raises(tmp_path):
    import xarray as xr
    from rime.era5.process import process_month
    files = write_month(tmp_path / "m", 2005, 3)
    ds = xr.open_dataset(files["sl_cp"], engine="h5netcdf").load()
    ds.isel(valid_time=[i for i in range(ds.sizes["valid_time"]) if i != 30]).to_netcdf(
        tmp_path / "gap.nc", engine="h5netcdf")
    files["sl_cp"] = tmp_path / "gap.nc"
    with pytest.raises(ValueError, match="hourly"):
        process_month(2005, 3, files, _conus())


def test_fetch_parallel_workers(tmp_paths):
    from rime.era5.download import load_manifest
    from rime.era5.process import fetch_era5
    fetch_era5((2005, 3), (2005, 4), workers=2, client_factory=SynthClient, conus=_conus())
    m = load_manifest()
    assert m["2005-03"]["status"] == m["2005-04"]["status"] == "done"
    assert len(pd.read_parquet(tmp_paths / "processed" / "era5_shares.parquet")) == (31 + 30) * 4
    assert not list((tmp_paths / "processed").glob("*.tmp"))


def test_era5_cli_accepts_pilot_options():
    from rime import cli
    cli._load_steps()
    called = {}
    import rime.era5.process as proc
    orig = cli._STEPS["era5"]
    cli._STEPS["era5"] = (lambda **kw: called.update(kw), *orig[1:])
    try:
        cli.main(["era5", "--start", "2015-07", "--end", "2015-07", "--max-months", "1", "--keep-raw", "--workers", "3"])
    finally:
        cli._STEPS["era5"] = orig
    assert called == {"start": (2015, 7), "end": (2015, 7), "max_months": 1, "keep_raw": True, "workers": 3}
