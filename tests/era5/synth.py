"""Synthetic ERA5-layout netCDF parts for tests."""
import calendar

import numpy as np
import pandas as pd
import xarray as xr

LAT = np.arange(40.0, 39.0, -0.25)   # 4 rows
LON = np.arange(-100.0, -99.0, 0.25)  # 4 cols


def _times(year, month, hours, days=None):
    days = days or range(1, calendar.monthrange(year, month)[1] + 1)
    return pd.to_datetime([f"{year}-{month:02d}-{d:02d}T{h}" for d in days for h in hours])


def _da(times, value, levels=None):
    shape = (len(times),) + ((len(levels),) if levels else ()) + (len(LAT), len(LON))
    data = np.broadcast_to(np.asarray(value, float), shape).copy()
    dims = ("valid_time",) + (("pressure_level",) if levels else ()) + ("latitude", "longitude")
    coords = {"valid_time": times, "latitude": LAT, "longitude": LON}
    if levels:
        coords["pressure_level"] = list(levels)
    return xr.DataArray(data, dims=dims, coords=coords)


def part_dataset(part, year, month, *, icing_rows=1, cp=0.0002, cape=1200.0):
    from rime.era5.download import HOURS4, ICING_LEVELS, PREV_HOURS, UPPER_LEVELS, HOURS24
    if part == "sl_cp_prev":
        py, pm = (year - 1, 12) if month == 1 else (year, month - 1)
        t = _times(py, pm, PREV_HOURS, [calendar.monthrange(py, pm)[1]])
        return xr.Dataset({"cp": _da(t, cp)})
    if part == "sl_cp":
        return xr.Dataset({"cp": _da(_times(year, month, HOURS24), cp)})
    t = _times(year, month, HOURS4)
    if part == "sl_cape":
        return xr.Dataset({"cape": _da(t, cape)})
    if part == "pl_icing":
        temp = _da(t, 280.0, ICING_LEVELS)
        temp[:, :, :icing_rows, :] = 263.0
        return xr.Dataset({"t": temp, "r": _da(t, 90.0, ICING_LEVELS), "clwc": _da(t, 2e-5, ICING_LEVELS)})
    if part == "pl_upper":
        z = _da(t, 0.0, UPPER_LEVELS)
        for i, h in enumerate((9160, 10360, 11780)):
            z[:, i] = h * 9.80665
        return xr.Dataset({"u": _da(t, 10.0, UPPER_LEVELS), "v": _da(t, 0.0, UPPER_LEVELS), "z": z,
                           "ciwc": _da(t, 0.0, UPPER_LEVELS)})
    raise KeyError(part)


def write_month(d, year, month, skip=(), **kw):
    from rime.era5.download import requests_for_month
    d.mkdir(parents=True, exist_ok=True)
    files = {}
    for part in requests_for_month(year, month):
        if part in skip:
            continue
        p = d / f"{part}.nc"
        part_dataset(part, year, month, **kw).to_netcdf(p, engine="h5netcdf")
        files[part] = p
    return files


class SynthClient:
    """Fake cdsapi client writing synthetic parts; `garbage=True` writes unreadable bytes."""

    def __init__(self, garbage=False):
        self.garbage, self.calls = garbage, 0

    def retrieve(self, name, request, target):
        from rime.era5.download import requests_for_month
        self.calls += 1
        if self.garbage:
            open(target, "wb").write(b"not netcdf")
            return
        y, m = int(request["year"][0]), int(request["month"][0])
        nxt = (y + 1, 1) if m == 12 else (y, m + 1)  # sl_cp_prev asks for the month before its target
        for year, month in ((y, m), nxt):
            match = [p for p, (_, r) in requests_for_month(year, month).items() if r == request]
            if match:
                part_dataset(match[0], year, month).to_netcdf(target, engine="h5netcdf")
                return
        raise AssertionError("unrecognized request")
