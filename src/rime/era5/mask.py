"""Contiguous-US land mask (48 states + DC) on the ERA5 grid, from Natural Earth via regionmask."""
import numpy as np
import xarray as xr

from rime import paths

EXCLUDE = {"Alaska", "Hawaii"}


def conus_mask(lat: np.ndarray, lon: np.ndarray, *, cache: bool = True) -> xr.DataArray:
    path = paths.PROCESSED / "conus_mask.nc"
    if cache and path.exists():
        m = xr.open_dataarray(path).load()
        if np.array_equal(m["latitude"], lat) and np.array_equal(m["longitude"], lon):
            return m.astype(bool)
    import regionmask

    states = regionmask.defined_regions.natural_earth_v5_0_0.us_states_50
    idx = states.mask(np.asarray(lon), np.asarray(lat))
    idx = idx.rename({d: n for d, n in zip(idx.dims, ("latitude", "longitude")) if d != n})
    keep = [n for n, name in zip(states.numbers, states.names) if name not in EXCLUDE]
    m = idx.isin(keep).rename("conus")
    m = m.assign_coords(latitude=lat, longitude=lon).transpose("latitude", "longitude")
    if cache:
        path.parent.mkdir(parents=True, exist_ok=True)
        m.astype("int8").to_netcdf(path)
    return m
