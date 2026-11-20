"""Solar elevation (NOAA general solar position approximation) and day/night consistency."""
import numpy as np
import pandas as pd

NIGHT = {"NITE", "NDRK", "NBRT"}
TWILIGHT_DEG = 6.0


def solar_elevation_deg(lat, lon, time_utc):
    scalar = np.ndim(lat) == 0 and np.ndim(lon) == 0 and np.ndim(np.asarray(time_utc, dtype=object)) == 0
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    t = pd.DatetimeIndex(np.atleast_1d(pd.to_datetime(time_utc)))
    doy = t.day_of_year.to_numpy()
    hours = (t.hour + t.minute / 60 + t.second / 3600).to_numpy()
    g = 2 * np.pi / 365 * (doy - 1 + (hours - 12) / 24)
    eqt = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g)
                    - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    decl = (0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g)
            + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g))
    tst = hours * 60 + eqt + 4 * lon               # true solar time, minutes
    ha = np.deg2rad(tst / 4 - 180)
    phi = np.deg2rad(lat)
    cos_zen = np.sin(phi) * np.sin(decl) + np.cos(phi) * np.cos(decl) * np.cos(ha)
    out = 90 - np.rad2deg(np.arccos(np.clip(cos_zen, -1, 1)))
    return float(out.ravel()[0]) if scalar else out


def daynight_mismatch(elev_deg, light_cond) -> np.ndarray:
    e = np.asarray(elev_deg, float)
    c = pd.Series(light_cond, dtype=object).fillna("").astype(str).str.strip().str.upper().to_numpy()
    day_wrong = (c == "DAYL") & (e < -TWILIGHT_DEG)
    night_wrong = np.isin(c, list(NIGHT)) & (e > TWILIGHT_DEG)
    return np.where(np.isfinite(e), day_wrong | night_wrong, False)
