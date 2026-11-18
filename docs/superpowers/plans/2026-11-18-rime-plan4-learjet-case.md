# rime Plan 4: Learjet 60 (Nov 1, 2026) weather reconstruction, preliminary

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconstruct the weather the Learjet 60 (N722BD, NTSB ERA27MA026) flew through near Greenacres, FL on 2026-11-01, using public radar and satellite data. Produce maps, numbers, and a factual write-up in `results/cases/learjet_2026-11-01/`, as spec §4d describes: an illustration of the method, **not** a cause determination.

**Architecture:**
- New subpackage `rime.cases`:
  - `geo.py`: distances, beam height, and gridding helpers (pure functions).
  - `nexrad.py`: fetches KAMX Level II volumes from the public `unidata-nexrad-level2` S3 bucket and computes composite reflectivity, 18-dBZ echo tops, and max reflectivity in the cruise layer on a lat/lon grid.
  - `goes.py`: fetches GOES-19 ABI L2 CMIPC band-13 brightness temperature.
  - `learjet.py`: CLI step `case-learjet`, not in `rime all`. It runs everything and writes figures and `facts.md`.

**Tech Stack:** existing, plus `xradar` (NEXRAD Level II reader), `matplotlib`; `regionmask` (already present) for coastlines/state outlines via Natural Earth.

**Spec:** `docs/superpowers/specs/2026-11-02-rime-design.md` §4d.

## Global Constraints

- **Public facts only** (NTSB statements via WPTV, 2026-11-02; NTSB ERA27MA026):
  - Departed Austin (AUS) about 10:37 a.m. ET, bound for North Eleuthera (ELH).
  - Cruise at 35,000 ft.
  - About 12:47 p.m.: light clear icing, moderate turbulence, OAT −47 °C (−53 °F), then precipitation; requested FL370.
  - Under 30 seconds later: descent and mayday.
  - About 12:48: overspeed and descent.
  - Impact about 12:51 p.m. near Military Trail and 10th Ave N, Greenacres.
  - Left elevator found 1.3–3.8 miles from the impact site.
  - EST applies (DST ended 2026-11-01 at 02:00), so the key times are 17:47, 17:48, and 17:51 UTC.
- **Impact point (approximate, from the intersection):** 26.6295 N, −80.1170 W. Labeled approximate everywhere.
- **The track is unknown until the NTSB preliminary report** (expected about 2026-12-01). The analysis uses rings (15/30/60 km) around the impact point plus a 60-km "approach sector" spanning bearings 250°–330° from impact. The route from Austin approaches from the WNW (great-circle bearing from impact to AUS ≈ 293°). The approach sector is a stated assumption, to be replaced by the real track.
- **Radar:** KAMX (Miami WSR-88D, 25.6111 N, −80.4128 W, 4 m elevation antenna height ignored → use site altitude from the file). Volumes 17:35–17:57 UTC.
  - Beam height uses the 4/3 effective Earth radius.
  - Echo top = the highest beam-center height with reflectivity ≥ 18 dBZ.
  - Cruise layer = 9.5–11.5 km MSL (FL310–FL380).
- **Satellite:** GOES-19 ABI-L2-CMIPC band 13 (10.3 µm), scans starting 17:41, 17:46, and 17:51 UTC. Brightness temperature is in K.
- **Wording:** every output says "preliminary; not a cause determination; NTSB's investigation is ongoing". No blame, no speculation about crew actions. Plain language.
- Raw downloads go to `data/raw/cases/` (gitignored). Figures and `facts.md` are committed.

## Review Focus

1. **Range-folded or missing gates and NaN reflectivity:** these are excluded, never treated as 0 dBZ or as "no echo top". Test in Task 1.
2. **Longitude/latitude order and units in distance and bearing helpers:** a sign error would put the storm on the wrong side of the impact point. Test against known distances (impact → KAMX ≈ 46 km... compute it, don't assume) in Task 1.
3. **Volume time vs sweep time:** a WSR-88D volume takes about 5 minutes. Stats report the volume start time and note the span. The 17:45:48 volume is the one bracketing the 17:47–17:48 events.
4. **GOES parallax:** high cloud tops appear displaced poleward and away from the satellite (GOES-19 at 75.2° W). At 26.6° N, a 12-km top shifts roughly 6–8 km north. The write-up states this, and the ring stats use radii (15/30/60 km) wide enough that it doesn't flip conclusions.

---

### Task 1: geo helpers

**Files:** Create `src/rime/cases/__init__.py`, `src/rime/cases/geo.py`; Test `tests/cases/test_geo.py`

**Interfaces:** Produces `haversine_km(lat1, lon1, lat2, lon2) -> float|ndarray`, `bearing_deg(lat1, lon1, lat2, lon2) -> float|ndarray` (initial bearing, 0 = north, clockwise), `beam_height_m(range_m, elev_deg, site_alt_m) -> ndarray` (4/3 Earth), `gate_latlon(site_lat, site_lon, range_m, azimuth_deg, elev_deg) -> (lat, lon)` (ground range from slant range), `in_sector(bearing, lo, hi) -> bool` (wraps at 360).

- [ ] **Step 1: Write failing tests:**
  - Haversine (0,0)-(0,1) ≈ 111.19 km.
  - Bearing from (26.63, −80.12) toward AUS (30.1945, −97.6699) is between 285 and 300.
  - `beam_height_m(100e3, 0.5°)` ≈ 1.46 km ± 0.05 above site.
  - `gate_latlon` of 50 km at azimuth 90 from (25, −80) → lat ≈ 25, lon ≈ −79.504 (±0.01).
  - `in_sector(355, 340, 20)` is True; `in_sector(30, 340, 20)` is False.
- [ ] **Step 2:** Run; expect FAIL. **Step 3:** Implement. **Step 4:** PASS. **Step 5:** Commit `feat(cases): geo helpers`.

### Task 2: NEXRAD products

**Files:** Create `src/rime/cases/nexrad.py`; Test `tests/cases/test_nexrad.py`

**Interfaces:**
- `list_volumes(site, start_utc, end_utc) -> list[str]`: S3 keys from the public bucket listing over HTTPS; skips `_MDM` files.
- `fetch_volume(key) -> Path`: uses `rime.download.fetch`, name `cases/<basename>`.
- `volume_points(path) -> pd.DataFrame`: one row per valid gate with `lat, lon, height_m, dbz, sweep_elev`. Reads with `xradar.io.open_nexradlevel2_datatree`, uses the `DBZH` field, and drops NaN gates.
- `grid_products(points, lat_edges, lon_edges) -> xr.Dataset`, per cell:
  - `composite_dbz`: max dBZ
  - `echo_top_km`: max `height_m`/1000 among gates ≥ 18 dBZ; NaN if no such gate
  - `cruise_max_dbz`: max dBZ among gates with 9.5 ≤ height ≤ 11.5 km

- [ ] **Step 1: Write failing tests on synthetic point frames:**
  - Two gates in one cell (30 dBZ at 5 km, 20 dBZ at 12 km) → composite 30, echo top 12.0, cruise_max NaN (no gate in the layer).
  - A gate of 10 dBZ at 13 km doesn't set the echo top.
  - A cell with no gates is NaN in all products (not 0).
  - Slow test: `list_volumes("KAMX", 2026-11-01T17:35, 17:57)` includes `KAMX20261101_174548_V06`.
- [ ] **Step 2:** FAIL. **Step 3:** Implement and add deps (`uv add xradar matplotlib`). **Step 4:** PASS. **Step 5:** Commit `feat(cases): NEXRAD level II products`.

### Task 3: GOES-19 band-13 brightness temperature

**Files:** Create `src/rime/cases/goes.py`; Test `tests/cases/test_goes.py`

**Interfaces:**
- `list_scans(start_utc, end_utc) -> list[str]` (CMIPC C13 keys)
- `fetch_scan(key) -> Path`
- `bt_latlon(path) -> xr.Dataset`, with `bt_k(y, x)`, `lat(y, x)`, `lon(y, x)`. Lat/lon are computed from the ABI fixed-grid projection (`goes_imager_projection` attributes) with the standard GOES-R PUG navigation equations; off-disk cells are NaN.

- [ ] **Step 1: Write failing tests:**
  - Navigation of the sub-satellite point: x = 0, y = 0 → lat 0, lon = `longitude_of_projection_origin` (−75.2).
  - A point off the Earth's disk → NaN.
  - Slow test: the 17:46 scan's bt_k is in [180, 320] K near the impact point.
- [ ] **Step 2–5:** as above. Commit `feat(cases): GOES-19 band-13 navigation`.

### Task 4: Case runner, figures, facts

**Files:** Create `src/rime/cases/learjet.py`, `results/cases/learjet_2026-11-01/`; register CLI `case-learjet` (`in_all=False`). Test `tests/cases/test_learjet.py`.

**Interfaces:**
- `ring_stats(products: xr.Dataset, center, radii_km=(15, 30, 60), sector=(250, 330)) -> pd.DataFrame`. Columns: `region, max_composite_dbz, max_echo_top_km, area_echo_top_ge_10_7km_km2, max_cruise_dbz`. Rows: one per ring, plus `approach_sector_60km`.
- `goes_stats(ds, center, radii_km) -> pd.DataFrame`. Columns: `region, min_bt_c, area_bt_le_minus60c_km2`.
- `run_case() -> None`. Writes:
  - `radar_composite_174548.png`: composite reflectivity, impact marker, rings, sector wedge, Florida outline
  - `radar_echotop_174548.png`
  - `goes_c13_1746.png`
  - `radar_stats.csv`, with every volume 17:35–17:57 × region
  - `goes_stats.csv`, with scans 17:41/17:46/17:51 × region
  - `facts.md`, written in plain language (see constraints): timeline, what the radar and satellite show near the impact point at 17:45–17:51 UTC, comparison of the −47 °C OAT with the standard atmosphere at FL350 (−54.3 °C), limitations (unknown track, parallax, volume timing, KAMX range ~70 km so the lowest beams overshoot low-level echoes), and "to be updated with the NTSB preliminary report".

- [ ] **Step 1: Write failing tests:**
  - `ring_stats` on a synthetic grid with one 12-km echo top 20 km from center → the 15-km ring has NaN or < 12, the 30-km ring has 12.
  - The sector excludes a cell due east of center.
  - `goes_stats` on a synthetic min of 200 K inside 15 km → min_bt_c ≈ −73.15.
- [ ] **Step 2:** FAIL. **Step 3:** Implement. **Step 4:** PASS, then `uv run rime case-learjet`. Expected: files written. Read `facts.md` and the CSVs, and sanity-check that the numbers match the figures.
- [ ] **Step 5:** Commit `feat(cases): Learjet 2026-11-01 preliminary weather reconstruction`.
