"""Turn each downloaded ERA5 month into per-time CONUS hazard shares, then delete the raw files."""
import calendar
import json
import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import xarray as xr

from rime import paths
from rime.cli import register
from rime.era5 import indices as ix
from rime.era5.download import download_month, load_manifest, manifest_path, month_dir, months_todo
from rime.era5.mask import conus_mask

INDEX_COLUMNS = ["icing", "turbulence", "convective", "hiwc"]
ANALYSIS_HOURS = (0, 6, 12, 18)


def _open(path: Path) -> xr.Dataset:
    ds = xr.open_dataset(path, engine="h5netcdf").load()
    for extra in ("number", "expver"):  # new-CDS netCDF may carry these scalar/aux coords
        if extra in ds.coords and ds[extra].ndim == 0:
            ds = ds.drop_vars(extra)
    return ds


def _shares(mask: xr.DataArray, conus: xr.DataArray) -> pd.Series:
    return ix.conus_share(mask, conus).to_series()


def process_month(year: int, month: int, files: dict[str, Path | None], conus: xr.DataArray) -> pd.DataFrame:
    icing_ds, upper, cape_ds, cp_ds = (_open(files[p]) for p in ("pl_icing", "pl_upper", "sl_cape", "sl_cp"))
    cp = cp_ds["cp"]
    if files.get("sl_cp_prev") is not None:
        cp = xr.concat([_open(files["sl_cp_prev"])["cp"], cp], "valid_time")
    cp = cp.sortby("valid_time")
    steps = cp["valid_time"].to_index().to_series().diff().dropna()
    if not (steps == pd.Timedelta(hours=1)).all():
        raise ValueError("convective precipitation is not hourly-contiguous (gap or duplicate hour)")
    times = cape_ds["valid_time"].to_index()
    times = times[(times.year == year) & (times.month == month) & times.hour.isin(ANALYSIS_HOURS)]

    cape = cape_ds["cape"].sel(valid_time=times)
    cp6 = ix.cp_6h(cp).reindex(valid_time=times)  # missing history → NaN, never zero
    icing = ix.icing_mask(*(icing_ds[v].sel(valid_time=times) for v in ("t", "r", "clwc")))
    turb = ix.turbulence_mask(*(upper[v].sel(valid_time=times) for v in ("u", "v", "z")))
    conv = ix.convective_mask(cape, cp6)
    hiwc = ix.hiwc_mask(cape, upper["ciwc"].sel(valid_time=times))
    out = pd.DataFrame({name: _shares(m, conus) for name, m in
                        zip(INDEX_COLUMNS, (icing, turb, conv, hiwc))})
    return out.rename_axis("time").reset_index()


_LOCK = threading.Lock()  # manifest and shares are shared by parallel month workers


def _atomic_write(path: Path, write) -> None:
    """write(tmp_path) then os.replace, so an interrupt never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    write(tmp)
    os.replace(tmp, path)


def _write_manifest(key: str, entry: dict) -> None:
    m = load_manifest()
    m[key] = entry
    _atomic_write(manifest_path(), lambda t: t.write_text(json.dumps(m, indent=2, sort_keys=True)))


def _append_shares(df: pd.DataFrame) -> None:
    p = paths.PROCESSED / "era5_shares.parquet"
    if p.exists():
        df = pd.concat([pd.read_parquet(p), df]).drop_duplicates("time", keep="last")
    df = df.sort_values("time")
    _atomic_write(p, lambda t: df.to_parquet(t, index=False))


def validate_month(year: int, month: int, df: pd.DataFrame) -> None:
    expected = calendar.monthrange(year, month)[1] * len(ANALYSIS_HOURS)
    if len(df) != expected:
        raise ValueError(f"{year}-{month:02d}: {len(df)} analysis times, expected {expected}")


def run_month(year: int, month: int, *, client=None, keep_raw: bool = False,
              conus: xr.DataArray | None = None) -> str:
    key = f"{year}-{month:02d}"
    d = month_dir(year, month)
    now = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        files = download_month(year, month, client=client)
        if conus is None:
            grid = _open(files["sl_cape"])
            conus = conus_mask(grid["latitude"].values, grid["longitude"].values)
        df = process_month(year, month, files, conus)
        validate_month(year, month, df)
    except Exception as e:  # recorded, never fatal for the batch
        status = f"failed:{type(e).__name__}: {str(e)[:200]}"
        with _LOCK:
            _write_manifest(key, {"status": status, "at": now()})
        if not keep_raw:
            shutil.rmtree(d, ignore_errors=True)  # a retry starts from clean downloads
        return status
    with _LOCK:
        _append_shares(df)
        _write_manifest(key, {"status": "done", "rows": len(df), "at": now()})
    if not keep_raw:
        shutil.rmtree(d, ignore_errors=True)
    return "done"


def annual_indices() -> pd.DataFrame:
    s = pd.read_parquet(paths.PROCESSED / "era5_shares.parquet")
    s["year"], s["ym"] = s["time"].dt.year, s["time"].dt.to_period("M")
    g = s.groupby("year")
    out = g[INDEX_COLUMNS].mean()
    out["n_months"] = g["ym"].nunique()
    out["complete"] = out["n_months"] == 12
    out = out.reset_index()
    out.to_parquet(paths.PROCESSED / "era5_annual.parquet", index=False)
    return out


def fetch_era5(start=(1990, 1), end=(2024, 12), max_months: int | None = None, *,
               keep_raw: bool = False, workers: int = 1, client_factory=None,
               conus: xr.DataArray | None = None) -> None:
    """Download and process months not yet done. `workers` months run concurrently
    (each holds its own CDS client); a pilot uses keep_raw=True to inspect the raw files."""
    todo = months_todo(start, end)[:max_months]
    print(f"  {len(todo)} months to fetch with {workers} worker(s)")

    def one(ym):
        client = client_factory() if client_factory else None
        status = run_month(*ym, client=client, keep_raw=keep_raw, conus=conus)
        print(f"  {ym[0]}-{ym[1]:02d}: {status}", flush=True)
        return status

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        statuses = list(pool.map(one, todo))
    if (paths.PROCESSED / "era5_shares.parquet").exists():
        annual_indices()
    print(f"  done: {statuses.count('done')}, failed: {len(statuses) - statuses.count('done')}")


def _ym(text: str) -> tuple[int, int]:
    y, m = text.split("-")
    return int(y), int(m)


def _configure(p) -> None:
    p.add_argument("--start", type=_ym, default=(1990, 1), help="first month, YYYY-MM")
    p.add_argument("--end", type=_ym, default=(2024, 12), help="last month, YYYY-MM")
    p.add_argument("--max-months", type=int, default=None)
    p.add_argument("--keep-raw", action="store_true", help="keep raw netCDF (pilot inspection)")
    p.add_argument("--workers", type=int, default=1, help="months downloaded concurrently")


register("era5", fetch_era5, "download + process ERA5 months (needs a Copernicus CDS account)",
         in_all=False, configure=_configure)
