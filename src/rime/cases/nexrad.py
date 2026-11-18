"""NEXRAD Level II volumes from the public AWS archive → gridded storm products."""
import re
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import xarray as xr

from rime.cases.geo import beam_height_m, gate_latlon
from rime.download import fetch

BUCKET = "https://unidata-nexrad-level2.s3.amazonaws.com"
TOP_DBZ = 18.0
CRUISE_KM = (9.5, 11.5)


def list_volumes(site: str, start: datetime, end: datetime) -> list[str]:
    keys, day = [], start.date()
    while day <= end.date():
        prefix = f"{day:%Y/%m/%d}/{site}/"
        xml = requests.get(f"{BUCKET}/?list-type=2&prefix={prefix}", timeout=60).text
        keys += re.findall(r"<Key>([^<]+)</Key>", xml)
        day += timedelta(days=1)
    out = []
    for k in keys:
        m = re.search(rf"{site}(\d{{8}}_\d{{6}})_V06$", k)
        if m and start <= datetime.strptime(m.group(1), "%Y%m%d_%H%M%S") <= end:
            out.append(k)
    return sorted(out)


def volume_time(key: str) -> datetime:
    return datetime.strptime(re.search(r"(\d{8}_\d{6})_V06", key).group(1), "%Y%m%d_%H%M%S")


def fetch_volume(key: str) -> Path:
    return fetch(f"{BUCKET}/{key}", f"cases/{Path(key).name}")


def volume_points(path: Path) -> pd.DataFrame:
    """Every valid reflectivity gate in the volume: lat, lon, beam-center height, dBZ."""
    import xradar  # noqa: F401  (registers the "nexradlevel2" engine)

    tree = xr.open_datatree(str(path), engine="nexradlevel2")
    root = tree.ds
    lat0, lon0, alt0 = (float(root[v]) for v in ("latitude", "longitude", "altitude"))
    frames = []
    for name in tree.children:
        if not name.startswith("sweep"):
            continue
        sw = tree[name].to_dataset()
        if "DBZH" not in sw:
            continue
        dbz = sw["DBZH"].values
        rng = sw["range"].values
        az = sw["azimuth"].values
        el = float(np.nanmedian(sw["elevation"].values))
        R, A = np.meshgrid(rng, az)
        ok = np.isfinite(dbz)
        if not ok.any():
            continue
        lat, lon = gate_latlon(lat0, lon0, R[ok], A[ok], el)
        frames.append(pd.DataFrame({"lat": lat, "lon": lon, "height_m": beam_height_m(R[ok], el, alt0),
                                    "dbz": dbz[ok], "sweep_elev": el}))
    return pd.concat(frames, ignore_index=True)


def grid_products(points: pd.DataFrame, lat_edges, lon_edges) -> xr.Dataset:
    """Per lat/lon cell: composite (max) dBZ, 18-dBZ echo top (km), max dBZ in the cruise layer."""
    lat_edges, lon_edges = np.asarray(lat_edges), np.asarray(lon_edges)
    p = points[(points.lat >= lat_edges[0]) & (points.lat < lat_edges[-1]) &
               (points.lon >= lon_edges[0]) & (points.lon < lon_edges[-1])].copy()
    p["i"] = np.digitize(p.lat, lat_edges) - 1
    p["j"] = np.digitize(p.lon, lon_edges) - 1
    shape = (len(lat_edges) - 1, len(lon_edges) - 1)

    def to_grid(s: pd.Series) -> np.ndarray:
        g = np.full(shape, np.nan)
        if len(s):
            idx = np.array(s.index.tolist())
            g[idx[:, 0], idx[:, 1]] = s.to_numpy()
        return g

    comp = to_grid(p.groupby(["i", "j"])["dbz"].max())
    top = to_grid(p[p.dbz >= TOP_DBZ].groupby(["i", "j"])["height_m"].max() / 1000)
    layer = p[(p.height_m >= CRUISE_KM[0] * 1000) & (p.height_m <= CRUISE_KM[1] * 1000)]
    cruise = to_grid(layer.groupby(["i", "j"])["dbz"].max())
    coords = {"lat": (lat_edges[:-1] + lat_edges[1:]) / 2, "lon": (lon_edges[:-1] + lon_edges[1:]) / 2}
    dims = ("lat", "lon")
    return xr.Dataset({"composite_dbz": (dims, comp), "echo_top_km": (dims, top),
                       "cruise_max_dbz": (dims, cruise)}, coords=coords)
