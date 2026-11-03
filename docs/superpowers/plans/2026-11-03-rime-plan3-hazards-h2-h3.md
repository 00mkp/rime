# rime Plan 3: hazard accidents, ERA5 hazard indices, H2/H3 tests

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the locked H2 and H3 tests end to end:
- hazard-specific accident counts and the per-hazard 2008 break check
- an ERA5 downloader
- the four ERA5 hazard indices over the contiguous US
- the H2a/H2b/H3a/H3b models

Everything except the real ERA5 download is built and tested on synthetic data now. The download needs the user's Copernicus CDS account, so it's a separate gated task at the end.

**Architecture:**
- `rime.hazards`: the accident side, pure NTSB data, runnable now.
- `rime.era5`: request builder and downloader, CONUS mask, index math, month processor. The month processor turns each downloaded month into per-time CONUS shares, then deletes the raw files.
- `rime.h2.run` (`rime h2`): models and outputs. It refuses to run without the `prereg-v1` tag, and reports missing indices instead of crashing.

**Tech Stack:** existing, plus `xarray`, `h5netcdf`, `cdsapi>=0.7.7`, `regionmask` (Natural Earth US states, small public download).

**Spec:** `docs/superpowers/specs/2026-11-02-rime-design.md`. **Binding:** `prereg/hypotheses.md` at tag `prereg-v1`, §3 H2/H3 table and text.

## Global Constraints

- The prereg is binding for codes, thresholds, levels, grid (0.25°), time step (00/06/12/18 UTC), periods (index 1990–2024; H2b per category primary period; H3b 2004–2024), model forms, tails, families, and minimum event counts (H2b ≥ 30 per hazard × category; H3b ≥ 20).
- **Hazard accident codes** (an aircraft counts for a hazard if any code matches):

  | Hazard | 2008 onward | Before 2008 |
  |---|---|---|
  | icing | finding prefix `03031025`; Events_Sequence last-3 `210` | Subj 20000 + Modifier 2213 |
  | turbulence | finding prefix `030320` except `03032025`; last-3 `360`, `362` | Subj 20000 + Modifier ∈ {2224, 2225, 2226, 2227, 2253, 2256} |
  | convective | finding prefix `030330`, `03034050`; last-3 `390` | Subj 20000 + Modifier ∈ {2208, 2215, 2216, 2228, 2238, 2239, 2241, 2242, 2243, 2244} |

- **H3 phase of flight:**
  - 2008 onward: the Events_Sequence code's first 3 digits are in 400–499 (en route).
  - Before 2008: `Occurrences.Phase_of_Flight` is in the cruise/climb/descent codes listed in `data/manual/phase_codes.csv`. Task 1 builds that file from the `ct_seqevt`/data dictionary meanings containing CRUISE, CLIMB, or DESCENT, excluding takeoff, initial climb, approach, and landing.
- **ERA5 levels:**
  - Icing: every ERA5 pressure level from 850 to 400 hPa (850, 825, 800, 775, 750, 700, 650, 600, 550, 500, 450, 400); variables `temperature`, `relative_humidity`, `specific_cloud_liquid_water_content`.
  - Turbulence: 300, 250, 200 hPa; variables `u_component_of_wind`, `v_component_of_wind`, `geopotential`.
  - H3: `specific_cloud_ice_water_content` at 300 and 250 hPa.
  - Single levels: `convective_available_potential_energy` at the 4 analysis hours, and `convective_precipitation` at all 24 hours (for 6-hour sums).
  - Area: N 50, W −125, S 24, E −66.
- **Index definitions** (each is the per-time share of CONUS land grid cells meeting the condition, then averaged to annual):
  - Icing: some icing level has 253.15 K ≤ T ≤ 273.15 K, RH ≥ 85%, and clwc ≥ 1e-5 kg/kg.
  - Turbulence: Ellrod TI1 = VWS × DEF ≥ 8e-7 s⁻² in either sub-layer 300–250 or 250–200 hPa.
    - VWS = |ΔV| / Δz, with Δz from geopotential / 9.80665.
    - DEF = sqrt((∂u/∂x − ∂v/∂y)² + (∂v/∂x + ∂u/∂y)²), using the sub-layer mean wind, with x and y derivatives on the sphere (R = 6,371,000 m) by centered differences.
  - Convective: CAPE ≥ 1000 J/kg and convective precipitation summed over the 6 hours ending at the analysis time ≥ 1 mm (cp is in metres, so ≥ 0.001).
  - H3 (HIWC proxy): CAPE ≥ 1500 J/kg and ciwc ≥ 5e-5 kg/kg at 300 or 250 hPa.
- **CONUS mask:** Natural Earth US states (regionmask `natural_earth_v5_0_0.us_states_50`), the 48 contiguous states + DC, on the ERA5 0.25° grid by cell center.
- Raw ERA5 files are deleted after each month is processed. Only `data/processed/era5_shares.parquet` (per time × index) and the annual indices are kept.
- Never run the real downloader without the user's CDS setup. `~/.cdsapirc` is never read or printed by code other than `cdsapi` itself.

## Review Focus

1. **The 6-hour convective-precip window at month boundaries:** 00 UTC on the 1st needs the previous month's last 5 hours. The processor must take them from the previous month's file (download one extra day), never treat them as zero. Test in Task 4.
2. **Ellrod derivatives at the grid edge:** centered differences are undefined on the outer row/column. Those cells are NaN and excluded from the share's denominator, not counted as "no turbulence". Test in Task 3.
3. **A month with missing or corrupt files:** the processor records it as failed in the manifest and the annual index marks that year incomplete. A year with fewer than 12 good months is excluded from H2a/H2b, never averaged over what's there. Test in Task 5.
4. **A hazard × category below the minimum event count:** reported as `descriptive` with its count, not tested and not dropped. Test in Task 6.
5. **Re-running the downloader after an interruption:** it skips months already processed (manifest), and it restarts a month whose raw file is partial. Test in Task 4.

---

### Task 1: Hazard accident classes, H3 phase crosswalk, per-hazard break check

**Files:**
- Create: `src/rime/hazards/__init__.py`, `src/rime/hazards/classes.py`, `data/manual/hazard_codes.csv`, `data/manual/phase_codes.csv`
- Modify: `scripts/check_coding_break.py`, which gains a per-hazard section
- Test: `tests/hazards/test_classes.py`

**Interfaces:**
- Produces: `hazard_flags(findings, events_seq, seq_of_events, *, aircraft) -> pd.DataFrame`, one row per `(ev_id, Aircraft_Key)` with bool columns `icing`, `turbulence`, `convective`.
- Produces: `enroute_flags(events_seq, occurrences, *, aircraft) -> pd.DataFrame`, with columns `ev_id, Aircraft_Key, enroute: bool`.
- Produces: `hazard_counts(events: pd.DataFrame, flags: pd.DataFrame, enroute: pd.DataFrame) -> pd.DataFrame`, with columns `year, category, hazard, count` (ACC only). Zero-filled over all years × categories × hazards present. There's an extra hazard `h3`: turbine categories (`airliner`, `charter`, `ga_turbine`), en route, any of the three hazards.
- Produces: `build_hazards() -> None` (CLI step `hazards`), writing `PROCESSED/hazard_counts.parquet`.

- [ ] **Step 1: Write failing tests:**
  - `test_icing_post2008_finding`: `"0303102512"` → icing True, others False.
  - `test_turbulence_excludes_wake`: `"0303202544"` → turbulence False.
  - `test_convective_microburst_post2008`: `"0303405011"` → convective True.
  - `test_occurrence_last3_maps`: Events_Sequence `402210` → icing; `404362` → turbulence; `508390` → convective.
  - `test_pre2008_modifiers`: (20000, 2213) → icing; (20000, 2256) → turbulence; (20000, 2208) → convective; (20000, 2203 crosswind) → none.
  - `test_enroute_post2008`: Events_Sequence `402210` → True; `508390` → False.
  - `test_enroute_pre2008`: Occurrences Phase_of_Flight equal to a cruise code from `phase_codes.csv` → True; a landing code → False.
  - `test_h3_counts_turbine_enroute_only`: a ga_piston en-route icing accident doesn't count toward `h3`; an airliner one does.
  - `test_counts_zero_filled`: a category-year with no events has count 0 rows for each hazard.
- [ ] **Step 2:** Build `phase_codes.csv` (columns `code,meaning,enroute`) from the pre-2008 phase table, Occurrences.Phase_of_Flight values joined to the `ct_seqevt` / `eADMSPUB_DataDictionary` meanings. Inspect it and commit.
- [ ] **Step 3:** Run `uv run pytest tests/hazards -q`. Expected: FAIL.
- [ ] **Step 4:** Implement it, driven by `hazard_codes.csv` (`hazard,system,table,match,code`) so the codes live in data, not code.
- [ ] **Step 5:** Run tests. Expected: PASS. Then run `uv run rime hazards` and `uv run python scripts/check_coding_break.py`. Expected: each hazard's 2008–10 / 2005–07 share ratio is printed, plus which hazards fall outside 0.67–1.5. Those hazards get a post-2008 indicator in H2b, per the prereg; record them in `results/qa/hazard_break.csv`.
- [ ] **Step 6:** Commit `feat(hazards): hazard accident classes, H3 phase crosswalk, per-hazard break check`.

### Task 2: CONUS mask and index math

**Files:**
- Create: `src/rime/era5/__init__.py`, `src/rime/era5/indices.py`, `src/rime/era5/mask.py`
- Test: `tests/era5/test_indices.py`, `tests/era5/test_mask.py`

**Interfaces:**
- Produces in `indices.py`:
  - `icing_mask(t, r, clwc) -> xr.DataArray[bool]`, any over `pressure_level`
  - `ellrod_ti1(u, v, z) -> xr.DataArray`, max over the two sub-layers, NaN at edges
  - `turbulence_mask(u, v, z) -> xr.DataArray[bool|NaN]`
  - `convective_mask(cape, cp6) -> xr.DataArray[bool]`
  - `hiwc_mask(cape, ciwc) -> xr.DataArray[bool]`
  - `conus_share(mask, conus) -> xr.DataArray`, indexed by time: the share of CONUS cells where mask is True, ignoring NaN cells
  - `cp_6h(cp_hourly) -> xr.DataArray`, the sum over the 6 hours ending at each timestamp; requires the 5 prior hours present, else NaN
- Dims follow ERA5 netCDF from the new CDS: `valid_time`, `pressure_level`, `latitude`, `longitude`.
- Produces in `mask.py`: `conus_mask(lat: np.ndarray, lon: np.ndarray) -> xr.DataArray[bool]`, cached to `PROCESSED/conus_mask.nc`.

- [ ] **Step 1: Write failing tests** (synthetic xarray, 1–2 times, 5×5 grid):
  - `test_icing_mask_requires_all_three`: T 263 K, RH 90, clwc 2e-5 at one level → True. Drop any one condition → False. T 250 K → False.
  - `test_icing_any_level`: the condition met only at 500 hPa → True.
  - `test_ellrod_known_value`: uniform shear flow u = a·y (stretching/shearing deformation DEF = a) with a vertical wind difference ΔV over Δz → TI1 ≈ (ΔV/Δz)·a within 5% at interior cells; edges NaN.
  - `test_turbulence_threshold`: TI1 just above / below 8e-7 → True / False.
  - `test_cp6_sums_window_and_needs_history`: hourly cp of 0.0002 m → at hour 5 the 6-hour sum = 0.0012; at hour 3 the result is NaN.
  - `test_convective_mask`: CAPE 1200 with cp6 0.0011 → True; CAPE 900 → False.
  - `test_hiwc_mask`: CAPE 1600 with ciwc 6e-5 at 250 hPa → True; at 400 hPa only → False (not a mask level).
  - `test_conus_share_ignores_nan`: 4 CONUS cells, 1 True, 1 NaN → share 1/3.
  - `test_conus_mask_excludes_ocean_and_canada` (slow; needs Natural Earth): point (39.0, −98.0) → True; (45.0, −60.0) → False; (49.9, −100.0) → False (Canada side); (25.0, −80.5) → True (Florida).
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. Add deps: `uv add xarray h5netcdf regionmask cdsapi`.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat(era5): CONUS mask and hazard index math`.

### Task 3: ERA5 request builder and resumable downloader

**Files:**
- Create: `src/rime/era5/download.py`
- Test: `tests/era5/test_download.py`

**Interfaces:**
- Produces: `requests_for_month(year: int, month: int) -> dict[str, tuple[str, dict]]`, mapping a part name to (CDS dataset name, request). Parts:
  - `pl_icing`: `reanalysis-era5-pressure-levels`, icing vars × icing levels, 4 hours
  - `pl_upper`: wind/geopotential at 300/250/200 plus ciwc at 300/250, 4 hours
  - `sl_cape`: `reanalysis-era5-single-levels`, CAPE, 4 hours
  - `sl_cp`: convective_precipitation, 24 hours, **including the last day of the previous month**
  - All parts use `area` [50, −125, 24, −66], `grid` [0.25, 0.25], `data_format` `netcdf`, `download_format` `unarchived`, `product_type` `reanalysis`.
- Produces: `download_month(year, month, *, client=None, raw_dir=RAW/"era5") -> dict[str, Path]`. It uses `cdsapi.Client()` when `client` is None, writes each part to `raw_dir/YYYY-MM/<part>.nc.part`, then renames on success.
- Produces: `months_todo(start=(1990, 1), end=(2024, 12)) -> list[tuple[int, int]]`, the months not marked `done` in `PROCESSED/era5_manifest.json`.

- [ ] **Step 1: Write failing tests** with a fake client whose `.retrieve(name, req, target)` writes a small file and records calls:
  - `test_request_parts_and_levels`: 2005-03 → 4 parts. `pl_icing` levels are exactly the 12 listed. `sl_cp` has 24 hours and days that include 2005-02-28.
  - `test_download_writes_parts_atomically`: after `download_month`, 4 `.nc` files exist and no `.part` files.
  - `test_partial_file_is_retried`: a pre-existing `.part` file is re-downloaded.
  - `test_months_todo_skips_done`: manifest marks 1990-01 done → it isn't in the list.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. Import `cdsapi` lazily inside `download_month`, so tests and import never touch `~/.cdsapirc`.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat(era5): month request builder and resumable downloader`.

### Task 4: Month processor and annual indices

**Files:**
- Create: `src/rime/era5/process.py`
- Test: `tests/era5/test_process.py`

**Interfaces:**
- Consumes: Tasks 2–3.
- Produces: `process_month(year, month, files: dict[str, Path], conus: xr.DataArray) -> pd.DataFrame`, with columns `time, icing, turbulence, convective, hiwc` (per-time CONUS shares) for the month's 00/06/12/18 UTC times only.
- Produces: `run_month(year, month, *, client=None, keep_raw=False) -> str`, returning `"done"` or `"failed:<reason>"`. It does download → process → append to `PROCESSED/era5_shares.parquet` (deduplicated on time) → manifest entry → delete raw unless keep_raw.
- Produces: `annual_indices() -> pd.DataFrame`, with columns `year, icing, turbulence, convective, hiwc, n_months, complete` (complete ⇔ n_months == 12), written to `PROCESSED/era5_annual.parquet`.
- Produces: `fetch_era5(start=(1990, 1), end=(2024, 12), max_months: int | None = None) -> None` (CLI step `era5`). It loops over `months_todo` and **is not registered in `rime all`**, because it needs the user's account.

- [ ] **Step 1: Write failing tests** using synthetic netCDF files written to `tmp_path` in ERA5 layout:
  - `test_process_month_shares`: a 2-day synthetic month with a known 25% icing area → icing share 0.25 at those times.
  - `test_cp_window_uses_previous_month`: the `sl_cp` file holds the previous day's last hours with cp → the 00 UTC on the 1st gets a finite cp6 (not NaN, not zero-filled).
  - `test_run_month_records_failure_on_corrupt_file`: a fake client writes garbage → returns `failed:...`, the manifest says failed, nothing is appended.
  - `test_annual_incomplete_year`: shares for 11 months of 1995 → `complete` False.
  - `test_raw_deleted_after_success`: after `run_month` with the fake client, the raw month dir is gone.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat(era5): month processor, manifest, annual indices`.

### Task 5: H2/H3 models and runner

**Files:**
- Create: `src/rime/h2/__init__.py`, `src/rime/h2/models.py`, `src/rime/h2/run.py`; Modify: `src/rime/cli.py` (register `rime.hazards.classes`, `rime.h2.run`)
- Test: `tests/h2/test_models.py`, `tests/h2/test_run.py`

**Interfaces:**
- Produces: `trend_test(years, index) -> Effect`, i.e. H2a/H3a. OLS `index ~ year` with Newey–West HAC (maxlags 2). rr holds the slope per decade, ci holds its 95% CI, p is two-sided. For H3a the p is one-sided positive, via `one_sided=True`.
- Produces: `link_test(counts: pd.Series, index: pd.Series, hours: pd.Series, *, break_2008: bool) -> Effect`, i.e. H2b/H3b.
  - Model: NB GLM, `count ~ z(index) + yc + yc²` (+ `post2008` if `break_2008`), offset `log(hours)`, ML dispersion via `smf.negativebinomial`, with Poisson-boundary handling as in `rime.h1.models._fit_nb`.
  - rr = exp(coef of z(index)) per 1 SD of the index. The p is one-sided positive.
- Produces: `run_h2() -> None` (CLI step `h2`).
  - Requires the `prereg-v1` tag (reuse `rime.h1.run.require_prereg_lock`).
  - If `era5_annual.parquet` is missing or has fewer than the needed complete years, it prints which years are missing, writes nothing, and exits 0.
  - Otherwise it writes `results/h2/confirmatory.csv` (families H2a, H2b, H3a, H3b; Holm within each), `results/h2/summary.md`, and `meta.json`.
  - H2b pairs below 30 events and H3b below 20 are status `descriptive`, with no p-value and excluded from Holm.
  - Index years exclude incomplete years. H2b uses each category's primary period (`rime.power.study_years`).

- [ ] **Step 1: Write failing tests** (synthetic):
  - `test_trend_detects_slope`: an index with slope 0.01/yr plus noise → p < 0.01, with the slope per decade ≈ 0.1 inside the CI.
  - `test_link_recovers_effect`: counts generated with RR 1.3 per SD → rr CI contains 1.3, one-sided p < 0.05.
  - `test_link_break_indicator_included`: `break_2008=True` adds a `post2008` term (check `model.exog_names`).
  - `test_run_h2_reports_missing_indices` (tmp paths): no era5_annual → returns without writing `results/h2/`, and prints "ERA5 indices missing".
  - `test_descriptive_below_minimum`: a pair with 12 events → status `descriptive`, absent from Holm.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `uv run pytest -q` (expected: all PASS), then `uv run rime h2`. Expected: the "ERA5 indices missing" message.
- [ ] **Step 5:** Commit `feat(h2): H2/H3 models and runner (awaiting ERA5)`.

### Task 6 (GATED on the user's CDS setup): pilot download, then the full run

- [ ] **Step 1:** The user confirms `~/.cdsapirc` exists and both dataset licenses are accepted. Check the file exists only (`test -f ~/.cdsapirc`); don't read it.
- [ ] **Step 2:** Pilot: `uv run rime era5` with `max_months=1` for 2015-07. Expected: a manifest `done` entry, 4 rows per day in `era5_shares.parquet`, and plausible shares: convective > 0 over CONUS in July, icing > 0. Report the wall time and download size to the user, and extrapolate the full-run duration.
- [ ] **Step 3:** With the user's OK, run the full download in the background (it's resumable). When it finishes, run `uv run rime h2` and report results the same way as Plan 2.
