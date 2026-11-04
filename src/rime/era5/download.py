"""ERA5 month requests for the CDS API, and a resumable per-month downloader.

`cdsapi` is imported only inside download_month, so importing this module or running
tests never touches the user's ~/.cdsapirc.
"""
import calendar
import json
from pathlib import Path

from rime import paths

PL = "reanalysis-era5-pressure-levels"
SL = "reanalysis-era5-single-levels"
AREA = [50, -125, 24, -66]  # N, W, S, E
ICING_LEVELS = (850, 825, 800, 775, 750, 700, 650, 600, 550, 500, 450, 400)
UPPER_LEVELS = (300, 250, 200)
HOURS4 = ["00:00", "06:00", "12:00", "18:00"]
HOURS24 = [f"{h:02d}:00" for h in range(24)]
PREV_HOURS = [f"{h:02d}:00" for h in range(19, 24)]


def _base(year: int, month: int, days: list[int], times: list[str]) -> dict:
    return {"product_type": ["reanalysis"], "year": [str(year)], "month": [f"{month:02d}"],
            "day": [f"{d:02d}" for d in days], "time": times, "area": AREA,
            "grid": [0.25, 0.25], "data_format": "netcdf", "download_format": "unarchived"}


def requests_for_month(year: int, month: int) -> dict[str, tuple[str, dict]]:
    days = list(range(1, calendar.monthrange(year, month)[1] + 1))
    py, pm = (year - 1, 12) if month == 1 else (year, month - 1)
    last_prev = calendar.monthrange(py, pm)[1]
    return {
        "pl_icing": (PL, {**_base(year, month, days, HOURS4),
                          "variable": ["temperature", "relative_humidity", "specific_cloud_liquid_water_content"],
                          "pressure_level": [str(p) for p in ICING_LEVELS]}),
        "pl_upper": (PL, {**_base(year, month, days, HOURS4),
                          "variable": ["u_component_of_wind", "v_component_of_wind", "geopotential",
                                       "specific_cloud_ice_water_content"],
                          "pressure_level": [str(p) for p in UPPER_LEVELS]}),
        "sl_cape": (SL, {**_base(year, month, days, HOURS4),
                         "variable": ["convective_available_potential_energy"]}),
        "sl_cp": (SL, {**_base(year, month, days, HOURS24), "variable": ["convective_precipitation"]}),
        "sl_cp_prev": (SL, {**_base(py, pm, [last_prev], PREV_HOURS), "variable": ["convective_precipitation"]}),
    }


def month_dir(year: int, month: int, raw_dir: Path | None = None) -> Path:
    return (raw_dir or paths.RAW / "era5") / f"{year}-{month:02d}"


def download_month(year: int, month: int, *, client=None, raw_dir: Path | None = None) -> dict[str, Path]:
    if client is None:
        import cdsapi
        client = cdsapi.Client(quiet=True)
    d = month_dir(year, month, raw_dir)
    d.mkdir(parents=True, exist_ok=True)
    files = {}
    for part, (name, request) in requests_for_month(year, month).items():
        final, partial = d / f"{part}.nc", d / f"{part}.nc.part"
        if not final.exists():
            partial.unlink(missing_ok=True)
            client.retrieve(name, request, str(partial))
            partial.replace(final)
        files[part] = final
    return files


def manifest_path() -> Path:
    return paths.PROCESSED / "era5_manifest.json"


def load_manifest() -> dict:
    p = manifest_path()
    return json.loads(p.read_text()) if p.exists() else {}


def months_todo(start=(1990, 1), end=(2024, 12)) -> list[tuple[int, int]]:
    done = {k for k, v in load_manifest().items() if v.get("status") == "done"}
    out, (y, m) = [], start
    while (y, m) <= end:
        if f"{y}-{m:02d}" not in done:
            out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out
