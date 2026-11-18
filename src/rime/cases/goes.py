"""GOES-19 ABI band-13 (10.3 µm) brightness temperature from the public AWS archive."""
import re
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import requests
import xarray as xr

from rime.download import fetch

BUCKET = "https://noaa-goes19.s3.amazonaws.com"
PRODUCT = "ABI-L2-CMIPC"


def list_scans(start: datetime, end: datetime) -> list[str]:
    keys, t = [], start.replace(minute=0, second=0, microsecond=0)
    while t <= end:
        prefix = f"{PRODUCT}/{t:%Y}/{t.timetuple().tm_yday:03d}/{t:%H}/"
        xml = requests.get(f"{BUCKET}/?list-type=2&prefix={prefix}", timeout=60).text
        keys += [k for k in re.findall(r"<Key>([^<]+)</Key>", xml) if "M6C13" in k]
        t += timedelta(hours=1)
    return sorted(k for k in keys if start <= scan_start(k) <= end)


def scan_start(key: str) -> datetime:
    s = re.search(r"_s(\d{4})(\d{3})(\d{2})(\d{2})(\d{2})", key).groups()
    return datetime(int(s[0]), 1, 1) + timedelta(days=int(s[1]) - 1, hours=int(s[2]),
                                                  minutes=int(s[3]), seconds=int(s[4]))


def fetch_scan(key: str) -> Path:
    return fetch(f"{BUCKET}/{key}", f"cases/{Path(key).name}")


def navigate(x, y, *, perspective_point_height, semi_major_axis, semi_minor_axis,
             longitude_of_projection_origin):
    """ABI fixed-grid scan angles (rad) → geodetic lat/lon (deg), GOES-R PUG Vol. 3 §4.2.8."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    r_eq, r_pol = semi_major_axis, semi_minor_axis
    H = perspective_point_height + r_eq
    a = np.sin(x) ** 2 + np.cos(x) ** 2 * (np.cos(y) ** 2 + (r_eq**2 / r_pol**2) * np.sin(y) ** 2)
    b = -2 * H * np.cos(x) * np.cos(y)
    c = H**2 - r_eq**2
    disc = b**2 - 4 * a * c
    with np.errstate(invalid="ignore"):
        rs = (-b - np.sqrt(np.where(disc >= 0, disc, np.nan))) / (2 * a)
    sx, sy, sz = rs * np.cos(x) * np.cos(y), -rs * np.sin(x), rs * np.cos(x) * np.sin(y)
    lat = np.degrees(np.arctan((r_eq**2 / r_pol**2) * sz / np.sqrt((H - sx) ** 2 + sy**2)))
    lon = longitude_of_projection_origin - np.degrees(np.arctan(sy / (H - sx)))
    return lat, lon


def bt_latlon(path: Path) -> xr.Dataset:
    ds = xr.open_dataset(path, engine="h5netcdf")
    p = ds["goes_imager_projection"].attrs
    X, Y = np.meshgrid(ds["x"].values, ds["y"].values)
    lat, lon = navigate(X, Y, **{k: float(p[k]) for k in (
        "perspective_point_height", "semi_major_axis", "semi_minor_axis", "longitude_of_projection_origin")})
    return xr.Dataset({"bt_k": (("y", "x"), ds["CMI"].values), "lat": (("y", "x"), lat),
                       "lon": (("y", "x"), lon)})
