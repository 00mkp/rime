"""ERA5 hazard masks and CONUS shares (prereg/hypotheses.md §3 H2/H3 table).

Masks are float DataArrays: 1.0 condition met, 0.0 not met, NaN undefined (e.g. grid edge).
Dims follow new-CDS ERA5 netCDF: valid_time, pressure_level, latitude, longitude.
"""
import numpy as np
import xarray as xr

G = 9.80665
R_EARTH = 6_371_000.0
ICING_T = (253.15, 273.15)   # −20 °C to 0 °C
ICING_RH = 85.0              # %
ICING_CLWC = 1e-5            # kg/kg (0.01 g/kg)
TI1_THRESHOLD = 8e-7         # s^-2
CAPE_CONV, CP6_CONV = 1000.0, 0.001   # J/kg, m (1 mm)
CAPE_HIWC, CIWC_HIWC = 1500.0, 5e-5   # J/kg, kg/kg (0.05 g/kg)
HIWC_LEVELS = (300, 250)
TURB_LAYERS = ((300, 250), (250, 200))


def _flag(cond: xr.DataArray, valid: xr.DataArray | None = None) -> xr.DataArray:
    out = cond.astype(float)
    return out.where(valid) if valid is not None else out


def icing_mask(t: xr.DataArray, r: xr.DataArray, clwc: xr.DataArray) -> xr.DataArray:
    cond = (t >= ICING_T[0]) & (t <= ICING_T[1]) & (r >= ICING_RH) & (clwc >= ICING_CLWC)
    return _flag(cond.any("pressure_level"))


def _ddx(f: xr.DataArray) -> xr.DataArray:
    coslat = np.cos(np.deg2rad(f["latitude"]))
    return f.differentiate("longitude") * (180 / np.pi) / (R_EARTH * coslat)


def _ddy(f: xr.DataArray) -> xr.DataArray:
    return f.differentiate("latitude") * (180 / np.pi) / R_EARTH


def _interior(f: xr.DataArray) -> xr.DataArray:
    lat, lon = f["latitude"], f["longitude"]
    inner = (lat != lat[0]) & (lat != lat[-1])
    inner = inner & (lon != lon[0]) & (lon != lon[-1])
    return f.where(inner)


def ellrod_ti1(u: xr.DataArray, v: xr.DataArray, z: xr.DataArray) -> xr.DataArray:
    """Ellrod–Knapp TI1 = VWS × DEF, max over the 300–250 and 250–200 hPa sub-layers."""
    layers = []
    for lo, up in TURB_LAYERS:
        sel = lambda f, p: f.sel(pressure_level=p, drop=True)
        dz = (sel(z, up) - sel(z, lo)) / G
        vws = np.hypot(sel(u, up) - sel(u, lo), sel(v, up) - sel(v, lo)) / dz
        um, vm = (sel(u, up) + sel(u, lo)) / 2, (sel(v, up) + sel(v, lo)) / 2
        dst = _ddx(um) - _ddy(vm)
        dsh = _ddx(vm) + _ddy(um)
        layers.append(_interior(vws * np.hypot(dst, dsh)))
    return xr.concat(layers, "layer").max("layer", skipna=False)


def turbulence_mask(u: xr.DataArray, v: xr.DataArray, z: xr.DataArray) -> xr.DataArray:
    ti = ellrod_ti1(u, v, z)
    return _flag(ti >= TI1_THRESHOLD, ti.notnull())


def cp_6h(cp_hourly: xr.DataArray) -> xr.DataArray:
    """Sum over the 6 hourly accumulations ending at each timestamp; NaN without full history."""
    return cp_hourly.rolling(valid_time=6, min_periods=6).sum()


def convective_mask(cape: xr.DataArray, cp6: xr.DataArray) -> xr.DataArray:
    return _flag((cape >= CAPE_CONV) & (cp6 >= CP6_CONV), cape.notnull() & cp6.notnull())


def hiwc_mask(cape: xr.DataArray, ciwc: xr.DataArray) -> xr.DataArray:
    levels = [p for p in HIWC_LEVELS if p in ciwc["pressure_level"].values]
    if not levels:
        return _flag(xr.zeros_like(cape, dtype=bool), cape.notnull())
    high = (ciwc.sel(pressure_level=levels) >= CIWC_HIWC).any("pressure_level")
    return _flag((cape >= CAPE_HIWC) & high, cape.notnull())


def conus_share(mask: xr.DataArray, conus: xr.DataArray) -> xr.DataArray:
    """Share of CONUS cells with mask == 1, among CONUS cells where mask is defined."""
    m = mask.where(conus)
    return (m == 1).sum(("latitude", "longitude")) / m.notnull().sum(("latitude", "longitude"))
