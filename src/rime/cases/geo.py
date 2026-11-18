"""Spherical-earth helpers for case reconstructions (degrees in, km/m out)."""
import numpy as np

R_EARTH_M = 6_371_000.0
KE = 4.0 / 3.0  # effective-earth-radius factor for standard radar refraction


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.deg2rad(lat1), np.deg2rad(lat2)
    dp, dl = p2 - p1, np.deg2rad(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R_EARTH_M / 1000 * np.arcsin(np.sqrt(a))


def bearing_deg(lat1, lon1, lat2, lon2):
    """Initial great-circle bearing from point 1 to point 2 (0 = north, clockwise)."""
    p1, p2 = np.deg2rad(lat1), np.deg2rad(lat2)
    dl = np.deg2rad(np.asarray(lon2) - np.asarray(lon1))
    x = np.sin(dl) * np.cos(p2)
    y = np.cos(p1) * np.sin(p2) - np.sin(p1) * np.cos(p2) * np.cos(dl)
    return np.rad2deg(np.arctan2(x, y)) % 360


def beam_height_m(range_m, elev_deg, site_alt_m):
    """Beam-center height (m MSL) for slant range and elevation, 4/3-earth model."""
    re = KE * R_EARTH_M
    r, th = np.asarray(range_m, float), np.deg2rad(elev_deg)
    return np.sqrt(r**2 + re**2 + 2 * r * re * np.sin(th)) - re + site_alt_m


def _ground_range_m(range_m, elev_deg):
    re = KE * R_EARTH_M
    r, th = np.asarray(range_m, float), np.deg2rad(elev_deg)
    h = np.sqrt(r**2 + re**2 + 2 * r * re * np.sin(th)) - re
    return re * np.arcsin(r * np.cos(th) / (re + h))


def gate_latlon(site_lat, site_lon, range_m, azimuth_deg, elev_deg):
    """Lat/lon of a radar gate: ground range along the azimuth from the site."""
    d = _ground_range_m(range_m, elev_deg) / R_EARTH_M
    az, p1, l1 = np.deg2rad(azimuth_deg), np.deg2rad(site_lat), np.deg2rad(site_lon)
    p2 = np.arcsin(np.sin(p1) * np.cos(d) + np.cos(p1) * np.sin(d) * np.cos(az))
    l2 = l1 + np.arctan2(np.sin(az) * np.sin(d) * np.cos(p1), np.cos(d) - np.sin(p1) * np.sin(p2))
    return np.rad2deg(p2), (np.rad2deg(l2) + 180) % 360 - 180


def in_sector(bearing, lo, hi):
    """True where bearing lies in [lo, hi] clockwise; handles wrap past 360."""
    b = np.asarray(bearing) % 360
    return (b >= lo) & (b <= hi) if lo <= hi else (b >= lo) | (b <= hi)
