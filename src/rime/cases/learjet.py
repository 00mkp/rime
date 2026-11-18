"""Preliminary weather reconstruction for the 2026-11-01 Learjet 60 crash (NTSB ERA27MA026).

An illustration of the rime method, not a cause determination.
"""
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xarray as xr  # noqa: E402

from rime import paths  # noqa: E402
from rime.cases import goes, nexrad  # noqa: E402
from rime.cases.geo import bearing_deg, haversine_km, in_sector  # noqa: E402
from rime.cli import register  # noqa: E402

IMPACT = (26.6295, -80.1170)   # approx.: Military Trail & 10th Ave N, Greenacres FL
KAMX = (25.6111, -80.4128)
RADII = (15, 30, 60)
SECTOR = (250, 330)            # assumed WNW approach (route from Austin); replace with NTSB track
FL350_KM = 10.7
ISA_FL350_C = -54.3
WINDOW = (datetime(2026, 11, 1, 17, 35), datetime(2026, 11, 1, 17, 57))
KEY_VOLUME = "KAMX20261101_174548_V06"
LAT_EDGES = np.arange(25.9, 27.41, 0.03)  # ~3 km: finer grids alias high-tilt beams at 117 km
LON_EDGES = np.arange(-81.1, -79.39, 0.03)
OUT = lambda: paths.RESULTS / "cases" / "learjet_2026-11-01"


def _regions(lat, lon, center):
    d = haversine_km(center[0], center[1], lat, lon)
    b = bearing_deg(center[0], center[1], lat, lon)
    regs = {f"within_{r}km": d <= r for r in RADII}
    regs["approach_sector_60km"] = (d <= 60) & in_sector(b, *SECTOR)
    return regs


def _cell_area_km2(lat2d, lon2d):
    dlat = np.abs(np.gradient(lat2d, axis=0)) * 111.2
    dlon = np.abs(np.gradient(lon2d, axis=1)) * 111.2 * np.cos(np.deg2rad(lat2d))
    return dlat * dlon


def ring_stats(products: xr.Dataset, center=IMPACT) -> pd.DataFrame:
    lat2d, lon2d = np.meshgrid(products.lat.values, products.lon.values, indexing="ij")
    area = _cell_area_km2(lat2d, lon2d)
    rows = []
    for name, m in _regions(lat2d, lon2d, center).items():
        sel = lambda v: products[v].values[m]
        top = sel("echo_top_km")
        mx = lambda a: float(np.nanmax(a)) if np.isfinite(a).any() else np.nan
        rows.append({"region": name, "max_composite_dbz": mx(sel("composite_dbz")),
                     "max_echo_top_km": mx(top),
                     "area_echo_top_ge_10_7km_km2": float(area[m][np.nan_to_num(top) >= FL350_KM].sum()),
                     "max_cruise_dbz": mx(sel("cruise_max_dbz"))})
    return pd.DataFrame(rows)


def goes_stats(ds: xr.Dataset, center=IMPACT) -> pd.DataFrame:
    lat, lon, bt = ds.lat.values, ds.lon.values, ds.bt_k.values
    ok = np.isfinite(lat) & np.isfinite(lon)
    area = np.nan_to_num(_cell_area_km2(np.where(ok, lat, np.nan), np.where(ok, lon, np.nan)))
    rows = []
    for name, m in _regions(np.where(ok, lat, 0), np.where(ok, lon, 0), center).items():
        m = m & ok & np.isfinite(bt)
        rows.append({"region": name,
                     "min_bt_c": float(bt[m].min() - 273.15) if m.any() else np.nan,
                     "area_bt_le_minus60c_km2": float(area[m & (bt <= 213.15)].sum())})
    return pd.DataFrame(rows)


def _outline(ax):
    import regionmask
    fl = regionmask.defined_regions.natural_earth_v5_0_0.us_states_50
    poly = fl[[n for n in fl.names if n == "Florida"][0]].polygon
    for g in getattr(poly, "geoms", [poly]):
        ax.plot(*g.exterior.xy, color="0.3", lw=0.8)


def _decorate(ax, title):
    _outline(ax)
    t = np.linspace(0, 2 * np.pi, 200)
    for r in RADII:
        ax.plot(IMPACT[1] + r / (111.2 * np.cos(np.deg2rad(IMPACT[0]))) * np.sin(t),
                IMPACT[0] + r / 111.2 * np.cos(t), color="k", lw=0.6, ls="--")
    for b in SECTOR:
        rb = np.deg2rad(b)
        ax.plot([IMPACT[1], IMPACT[1] + 60 / (111.2 * np.cos(np.deg2rad(IMPACT[0]))) * np.sin(rb)],
                [IMPACT[0], IMPACT[0] + 60 / 111.2 * np.cos(rb)], color="k", lw=0.6)
    ax.plot(IMPACT[1], IMPACT[0], marker="x", color="red", ms=10, mew=2, label="impact (approx.)")
    ax.set_xlim(LON_EDGES[0], LON_EDGES[-1])
    ax.set_ylim(LAT_EDGES[0], LAT_EDGES[-1])
    ax.set_aspect(1 / np.cos(np.deg2rad(IMPACT[0])))
    ax.set_title(title, fontsize=10)
    ax.legend(loc="lower left", fontsize=8)


def _map(field, title, label, path, cmap, vmin, vmax, lon=None, lat=None):
    fig, ax = plt.subplots(figsize=(7, 6.5), dpi=130)
    if lon is None:
        im = ax.pcolormesh(LON_EDGES, LAT_EDGES, field, cmap=cmap, vmin=vmin, vmax=vmax, shading="flat")
    else:
        im = ax.pcolormesh(lon, lat, field, cmap=cmap, vmin=vmin, vmax=vmax, shading="nearest")
    fig.colorbar(im, ax=ax, shrink=0.8, label=label)
    _decorate(ax, title)
    fig.text(0.01, 0.01, "Preliminary; not a cause determination. Rings 15/30/60 km; wedge = assumed approach sector.",
             fontsize=7, color="0.3")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def run_case() -> None:
    out = OUT()
    out.mkdir(parents=True, exist_ok=True)
    radar_rows, key_products = [], None
    for key in nexrad.list_volumes("KAMX", *WINDOW):
        prod = nexrad.grid_products(nexrad.volume_points(nexrad.fetch_volume(key)), LAT_EDGES, LON_EDGES)
        s = ring_stats(prod).assign(volume_start_utc=nexrad.volume_time(key).isoformat())
        radar_rows.append(s)
        if key.endswith(KEY_VOLUME):
            key_products = prod
        print(f"  radar {nexrad.volume_time(key):%H:%M:%S}")
    radar = pd.concat(radar_rows, ignore_index=True)
    radar.to_csv(out / "radar_stats.csv", index=False)

    goes_rows, key_bt = [], None
    for key in goes.list_scans(datetime(2026, 11, 1, 17, 40), datetime(2026, 11, 1, 17, 52)):
        ds = goes.bt_latlon(goes.fetch_scan(key))
        box = (ds.lat >= LAT_EDGES[0]) & (ds.lat <= LAT_EDGES[-1]) & (ds.lon >= LON_EDGES[0]) & (ds.lon <= LON_EDGES[-1])
        ys, xs = np.where(box.values)
        ds = ds.isel(y=slice(ys.min(), ys.max() + 1), x=slice(xs.min(), xs.max() + 1))
        t = goes.scan_start(key)
        goes_rows.append(goes_stats(ds).assign(scan_start_utc=t.isoformat()))
        if t.minute == 46:
            key_bt = ds
        print(f"  goes {t:%H:%M:%S}")
    sat = pd.concat(goes_rows, ignore_index=True)
    sat.to_csv(out / "goes_stats.csv", index=False)

    _map(key_products.composite_dbz.values, "KAMX composite reflectivity, volume start 17:45:48 UTC",
         "dBZ (column max)", out / "radar_composite_174548.png", "turbo", 0, 70)
    _map(key_products.echo_top_km.values, "KAMX 18-dBZ echo tops, volume start 17:45:48 UTC",
         "echo top (km MSL); FL350 ≈ 10.7 km", out / "radar_echotop_174548.png", "viridis", 0, 16)
    _map(key_bt.bt_k.values - 273.15, "GOES-19 band 13 (10.3 µm), scan start 17:46 UTC",
         "brightness temperature (°C)", out / "goes_c13_1746.png", "gray_r", -80, -20,
         lon=key_bt.lon.values, lat=key_bt.lat.values)
    key_path = nexrad.fetch_volume([k for k in nexrad.list_volumes("KAMX", *WINDOW) if k.endswith(KEY_VOLUME)][0])
    sweeps = nexrad.sweep_times(key_path, float(haversine_km(*IMPACT, *KAMX)))
    sweeps.to_csv(out / "radar_sweep_times_174548.csv", index=False)
    (out / "facts.md").write_text(render_facts(radar, sat, sweeps))
    print(f"  wrote {out}")


def _fmt(x, nd=1):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/a"
    return f"{x:.{nd}f}".replace("-", "−")


WPTV = "https://www.wptv.com/news/palm-beach-county/region-c-palm-beach-county/ntsb-news-conference-learjet-60-crash-in-palm-beach-county/11-2-26"


def render_facts(radar: pd.DataFrame, sat: pd.DataFrame, sweeps: pd.DataFrame) -> str:
    k = radar[radar.volume_start_utc == "2026-11-01T17:45:48"].set_index("region")
    g = sat[sat.scan_start_utc.str.startswith("2026-11-01T17:46")].set_index("region")
    dist = float(haversine_km(*IMPACT, *KAMX))
    upper = sweeps[(sweeps.height_km_at_range >= 8) & (sweeps.height_km_at_range <= 14.5)]
    tilts = ", ".join(f"{e:.1f}° (beam centre ≈ {h:.1f} km)".replace("-", "−")
                      for e, h in zip(upper.elevation, upper.height_km_at_range))
    t0, t1 = upper.start_utc.min(), upper.end_utc.max()
    names = {"within_15km": "within 15 km", "within_30km": "within 30 km", "within_60km": "within 60 km",
             "approach_sector_60km": "assumed approach sector (60 km)"}
    table = [
        "| Area (grid cells whose centres lie within…) | Max reflectivity (dBZ) | Highest 18-dBZ echo top (km MSL) | Area with echo tops ≥ 10.7 km | Max reflectivity at 9.5–11.5 km (dBZ) | Coldest band-13 brightness temperature (°C), scan 17:46 | Area ≤ −60 °C |",
        "|---|---|---|---|---|---|---|",
    ]
    for r, label in names.items():
        table.append(f"| {label} | {_fmt(k.loc[r, 'max_composite_dbz'])} | {_fmt(k.loc[r, 'max_echo_top_km'])} | "
                     f"{_fmt(k.loc[r, 'area_echo_top_ge_10_7km_km2'], 0)} km² | {_fmt(k.loc[r, 'max_cruise_dbz'])} | "
                     f"{_fmt(g.loc[r, 'min_bt_c'])} | {_fmt(g.loc[r, 'area_bt_le_minus60c_km2'], 0)} km² |")
    blocks = [
        "# Learjet 60 crash near Greenacres, FL (2026-11-01): preliminary weather reconstruction",
        "**Preliminary; not a cause determination.** NTSB's investigation (ERA27MA026) is ongoing. This page shows what public radar and satellite data recorded near the crash, as an illustration of rime's method. It will be updated when NTSB publishes the flight track in its preliminary report (expected around 2026-12-01).",
        "## What NTSB has said (as reported by WPTV from NTSB's 2026-11-02 news conference)",
        "\n".join([
            "- The flight departed Austin, TX about 10:37 a.m. ET for North Eleuthera, Bahamas, cruising at 35,000 ft.",
            "- About 12:47 p.m. ET (17:47 UTC), the crew reported light clear icing, moderate turbulence, an outside air temperature of −47 °C (−53 °F), and then precipitation, and requested a climb to 37,000 ft. NTSB has not characterized the icing further.",
            "- Less than 30 seconds later they announced a descent and a mayday. About 12:48 they reported an overspeed condition and descent. Impact was about 12:51 p.m. ET (17:51 UTC).",
            "- Investigators have \"some indication that the aircraft was breaking before impact\", which NTSB describes as preliminary. Most of the left elevator was found in pieces 1.3–3.8 miles (2.1–6.1 km) from the impact site.",
        ]),
        "## What the weather data show",
        f"Radar: Miami WSR-88D (KAMX), {dist:.0f} km south-southwest of the impact point. The volume scan starting 17:45:48 UTC is the closest to the 17:47–17:48 UTC events. "
        f"Within it, the tilts that sample about 8–14 km above the impact area ({tilts}) were taken between {t0} and {t1} UTC, "
        "roughly 1–2 minutes after the icing report and before impact.",
        "\n".join(table),
        "Satellite: GOES-19 ABI band 13 (10.3 µm). For thick cloud, the brightness temperature approximates the cloud-top temperature. The CONUS scan starting 17:46:17 UTC covered this area by 17:48:56.",
        f"For context, the reported outside air temperature (−47 °C) is about {(-47 - ISA_FL350_C):.0f} °C warmer than the standard atmosphere at 35,000 ft ({_fmt(ISA_FL350_C)} °C). "
        "35,000 ft is a pressure altitude, about 10.7 km in the standard atmosphere and roughly 0.2–0.3 km higher in geometric height on a day this warm. The radar heights above are geometric.",
        "Every radar volume from 17:35 to 17:57 UTC and every satellite scan from 17:41 to 17:51 UTC is in `radar_stats.csv` and `goes_stats.csv`. Sweep times for the key volume are in `radar_sweep_times_174548.csv`.",
        "## Limitations",
        "\n".join([
            "- **Track unknown.** Until NTSB publishes it, the analysis uses rings around the approximate impact point, plus a 60-km wedge to the west-northwest (bearings 250°–330°, the direction of the route from Austin). The wedge is an assumption.",
            "- **Impact point is approximate:** the intersection named in news reports. Areas are built from ~3-km grid cells, so a value can come from a cell just inside a ring's edge.",
            f"- **Radar geometry:** at {dist:.0f} km from KAMX, the beam is ~2 km deep, and the lowest beam passes about 1.5–2 km above the ground, so low-level rain is undersampled. Upper levels are sampled by only a few tilts whose beam centres are 2–3 km apart. Echo tops are therefore quantized by tilt and uncertain to within about 1–3 km. The cruise layer is sampled by two tilts with ~2 km vertical resolution.",
            "- **Satellite parallax:** high cloud tops appear displaced about 7–9 km toward the north-northwest (away from the satellite). That's small compared with the 15–60 km areas used here.",
        ]),
        "## Sources",
        "\n".join([
            "- NTSB investigation page: https://www.ntsb.gov/investigations/Pages/ERA27MA026.aspx",
            f"- NTSB statements as reported by WPTV, 2026-11-02: {WPTV}",
            "- NEXRAD Level II, KAMX: `unidata-nexrad-level2` public AWS bucket",
            "- GOES-19 ABI L2 CMIPC band 13: `noaa-goes19` public AWS bucket",
        ]),
    ]
    return "\n\n".join(blocks) + "\n"


register("case-learjet", run_case, "Learjet 2026-11-01 preliminary weather reconstruction", in_all=False)
