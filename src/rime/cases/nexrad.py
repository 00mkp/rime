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


FILL_MAX_DBZ = -32.5  # xradar decodes raw code 0 (below threshold) to −33.0 and 1 (range folded) to −32.5


def valid_dbz(dbz: np.ndarray) -> np.ndarray:
    """True for real reflectivity; False for NaN and the Level II fill codes."""
    dbz = np.asarray(dbz, float)
    return np.isfinite(dbz) & (dbz > FILL_MAX_DBZ)


def _open(path: Path):
    import xradar  # noqa: F401  (registers the "nexradlevel2" engine)

    return xr.open_datatree(str(path), engine="nexradlevel2")


def sweep_times(path: Path, range_km: float) -> pd.DataFrame:
    """Per reflectivity sweep: elevation, first/last ray time (UTC), beam-centre height at range_km."""
    tree = _open(path)
    alt0 = float(tree.ds["altitude"])
    rows = []
    for name in tree.children:
        sw = tree[name].to_dataset()
        if not name.startswith("sweep") or "DBZH" not in sw:
            continue
        t = pd.to_datetime(sw["time"].values)
        el = float(np.nanmedian(sw["elevation"].values))
        rows.append({"elevation": round(el, 1), "start_utc": f"{t.min():%H:%M:%S}", "end_utc": f"{t.max():%H:%M:%S}",
                     "height_km_at_range": round(float(beam_height_m(range_km * 1000, el, alt0)) / 1000, 1)})
    return pd.DataFrame(rows)


def volume_points(path: Path) -> pd.DataFrame:
    """Every valid reflectivity gate in the volume: lat, lon, beam-center height, dBZ."""
    tree = _open(path)
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
        ok = valid_dbz(dbz)
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
