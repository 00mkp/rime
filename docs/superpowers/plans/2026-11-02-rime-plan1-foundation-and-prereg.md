# rime Plan 1: Foundation, Part 1 data, and pre-registration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the reproducible data foundation for Part 1 (NTSB accidents, ENSO phases, flight-hour exposure), run the power analysis, and produce a pre-registration of H1–H3 for the user to approve and lock with the `prereg-v1` tag.

**Architecture:** A Python package `rime` with a small argparse CLI (`uv run rime <step>`). Each step reads cached raw downloads or committed manual tables and writes Parquet under `data/`. Raw downloads are cached with a checksum manifest. Analysis code never sees weather-coded outcomes split by ENSO or hazard before the `prereg-v1` tag exists.

**Tech Stack:** Python ≥3.12 via uv; pandas, pyarrow, numpy, scipy, statsmodels, access-parser (pure-Python Access `.mdb` reader, verified on `avall.mdb` 2026-11-02), openpyxl, requests; pytest.

**Spec:** `docs/superpowers/specs/2026-11-02-rime-design.md`

**Scope of this plan:** spec §3 up to and including the pre-registration gate, plus the shared foundation. Later plans: Plan 2 (Part 1 confirmatory analysis + H2/H3 ERA5 hazard series + ASRS corroboration), Plan 3 (Part 2 catalogs + cross-reference), Plan 4 (report site + Learjet case).

## Global Constraints

- Free, public data only. No OpenSky research application.
- US only; study period about 1990 to now (a source's own floor overrides).
- Aircraft categories, analyzed separately and never pooled into a headline: `airliner` (Part 121), `charter` (Part 135 fixed-wing), `ga_turbine`, `ga_piston` (Part 91/125/133/137 fixed-wing), `helicopter` (any Part except 121). Out of scope: drones (`unmanned == 'Y'`), gliders, balloons, weight-shift, gyroplanes, powered parachutes, ultralights, unknown category.
- Business jets get a flag (`is_business_jet`), not their own category.
- Alaska and Hawaii are their own regions.
- Before `prereg-v1`, the only outcome data computed or viewed is **counts per category per year** (all-accident and weather-involved). No split by ENSO phase, region × season, or hazard type.
- Laptop scale; one command (`uv run rime all`) rebuilds everything from cache/raw.
- Open source; no personal setup details in repo files. Public GitHub repo from day one.
- Lowercase project name `rime` in all user-visible text.
- Fixed RNG seed `20261102` wherever randomness is used.

## Review Focus

1. **Events present in both `Pre2008.mdb` and `avall.mdb`** should be counted once (dedupe on `ev_id`, keep the `avall` row). Test in Task 2.
2. **Multi-aircraft events (midair collisions)** should yield one row per aircraft, each with its own category. Event-level totals must not double-count. Test in Task 7.
3. **Missing or odd location data** (null `ev_state`, territories like PR/GU/VI, foreign `ev_country`) should map to region `excluded_location` and be reported in the data-quality output, never raise. Test in Task 3.
4. **The trailing end of the ONI record**, where a run of ≥0.5 seasons is shorter than 5 because the series ends (e.g., 2026), should be labeled with its tentative phase and `provisional=True`, not neutral. Test in Task 5.
5. **A category-year with no sourced exposure** should be dropped from rate calculations and listed, never treated as zero hours or zero rate. Test in Task 6.

---

### Task 1: Repo scaffold and cached downloader

**Files:**
- Create: `pyproject.toml`, `README.md`, `.gitignore`, `src/rime/__init__.py`, `src/rime/paths.py`, `src/rime/download.py`, `src/rime/cli.py`
- Test: `tests/test_download.py`

**Interfaces:**
- Produces: `rime.paths.ROOT`, `RAW`, `INTERIM`, `PROCESSED`, `MANUAL`, `RESULTS` (`pathlib.Path`; `data/raw`, `data/interim`, `data/processed`, `data/manual`, `results`). `RIME_DATA_DIR` env var overrides the `data/` root (tests use `tmp_path`).
- Produces: `rime.download.fetch(url: str, name: str, *, force: bool = False) -> Path` saves to `RAW/name`. It skips the download when the file is present and its sha256 matches the manifest. It writes `RAW/MANIFEST.json` entries `{name: {url, sha256, bytes, retrieved_at_utc}}`.
- Produces: `rime.cli.main(argv: list[str] | None = None) -> int` with subcommands registered by later tasks via `register(name, func, help)`. The `all` subcommand runs registered steps in registration order.

- [ ] **Step 1:** `git init` in `PersonalProjects/rime`. Commit the existing spec and this plan on `main` ("docs: rime design spec and plan 1"). Then `git switch -c plan1-foundation`.
- [ ] **Step 2:** Create `pyproject.toml` (package `rime`, src layout, `requires-python = ">=3.12"`, the deps above, `[project.scripts] rime = "rime.cli:main"`, pytest dev group). `.gitignore` ignores `data/raw/`, `data/interim/`, `data/processed/`, `.venv/`. `README.md` has a one-paragraph purpose and `uv sync && uv run rime all`.
- [ ] **Step 3: Write failing tests** in `tests/test_download.py`, using a local `http.server` fixture serving a 1 KB file:
  - `test_fetch_downloads_and_records_manifest`: the file exists; manifest has the url, the correct sha256 and bytes.
  - `test_fetch_skips_when_cached`: the second call makes 0 requests (count server hits).
  - `test_fetch_redownloads_on_checksum_mismatch`: corrupt the file → the next call re-downloads.
- [ ] **Step 4:** Run `uv run pytest tests/test_download.py -v`. Expected: FAIL (module missing).
- [ ] **Step 5:** Implement `paths.py`, `download.py` (stream to `name.part`, then rename), and `cli.py`.
- [ ] **Step 6:** Run `uv run pytest -v`. Expected: PASS. `uv run rime --help` lists `all`.
- [ ] **Step 7:** Commit `feat: scaffold rime package and cached downloader`.

### Task 2: NTSB ingest

**Files:**
- Create: `src/rime/ntsb/__init__.py`, `src/rime/ntsb/ingest.py`
- Test: `tests/ntsb/test_ingest.py`

**Interfaces:**
- Consumes: `fetch`.
- Produces: `rime.ntsb.ingest.SOURCES = {"avall": "https://data.ntsb.gov/avdata/FileDirectory/DownloadFile?fileID=avall.zip", "pre2008": "https://data.ntsb.gov/avdata/FileDirectory/DownloadFile?fileID=Pre2008.zip"}`
- Produces: `TABLES = ["events", "aircraft", "engines", "Findings", "Events_Sequence", "Occurrences", "seq_of_events", "narratives"]`
- Produces: `read_mdb_table(mdb: Path, table: str) -> pd.DataFrame` (access-parser `parse_table` → DataFrame; empty table → empty frame with columns).
- Produces: `combine(avall: pd.DataFrame, pre2008: pd.DataFrame, key: str = "ev_id") -> pd.DataFrame`. Concatenates with a `source_db` column (`"avall"`/`"pre2008"`). For `ev_id`s present in both, it keeps only the avall rows.
- Produces: `ingest() -> None` (CLI step `ntsb`). Fetches and unzips both files, then writes `INTERIM/ntsb/<table>.parquet` per table in `TABLES`.

- [ ] **Step 1: Write failing tests:**
  - `test_combine_prefers_avall_on_overlap`: avall `{ev_id: ["A","B"]}`, pre2008 `{ev_id: ["B","C"]}` → `ev_id` `["A","B","C"]`; `B` has `source_db == "avall"`.
  - `test_combine_handles_child_tables`: two `Findings` rows for `B` in each source → only the avall's 2 survive.
  - `test_read_mdb_table_real_file` (marked `@pytest.mark.slow`, skipped if `RAW/avall.mdb` absent): `events` has columns including `ev_id, ev_date, dec_latitude, dec_longitude, ev_state, ev_country, ev_highest_injury, wx_cond_basic`, and more than 25,000 rows.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. The Pre2008 `Occurrences` (which has `Altitude`, `Phase_of_Flight`) and `seq_of_events` are populated only in pre2008. In avall they're empty, which is fine.
- [ ] **Step 4:** Run `uv run pytest -v`, then `uv run rime ntsb` (about 250 MB download). Expected: PASS. Parquet files exist. Print row counts per table per source.
- [ ] **Step 5:** Commit `feat: ingest NTSB avall + Pre2008 databases`.

### Task 3: Regions and aircraft categories

**Files:**
- Create: `data/manual/regions.csv`, `src/rime/ntsb/classify.py`
- Test: `tests/ntsb/test_classify.py`

**Interfaces:**
- Produces: `region_for(ev_country: str | None, ev_state: str | None) -> str`. Returns one of the 9 NCEI climate regions (`northeast, upper_midwest, ohio_valley, southeast, northern_rockies_plains, south, southwest, northwest, west`), `alaska`, `hawaii`, or `excluded_location`.
- Produces: `category_for(acft_category, far_part, eng_type, unmanned) -> str | None`. Returns a category name, or None when out of scope.
- Produces: `is_business_jet(acft_category, far_part, eng_type) -> bool`.

`regions.csv` (`state,region`), the NCEI U.S. climate regions:
northeast: CT DE ME MD MA NH NJ NY PA RI VT DC · upper_midwest: IA MI MN WI · ohio_valley: IL IN KY MO OH TN WV · southeast: AL FL GA NC SC VA · northern_rockies_plains: MT NE ND SD WY · south: AR KS LA MS OK TX · southwest: AZ CO NM UT · northwest: ID OR WA · west: CA NV · alaska: AK · hawaii: HI.

Category rules, applied in order:
1. `unmanned == 'Y'` → None.
2. `acft_category == 'HELI'` and `far_part != '121'` → `helicopter`.
3. `acft_category != 'AIR'` → None.
4. `far_part == '121'` → `airliner`.
5. `far_part == '135'` → `charter`.
6. `far_part` in {`091`, `091K`, `091F`, `125`, `133`, `137`} → `ga_turbine` if `eng_type` in {TF, TJ, TP, TS, GTFN}, else `ga_piston` if `eng_type` in {REC, ELEC}, else None.
7. Anything else (`129`, `PUBU`, `NUSN`, `NUSC`, `UNK`, null) → None.

`is_business_jet`: `acft_category == 'AIR'` and `eng_type` in {TF, TJ, GTFN} and `far_part` in {`091`, `091K`, `135`}.

- [ ] **Step 1: Write failing tests** (parametrized):
  - `region_for("USA","FL") == "southeast"`, `("USA","AK") == "alaska"`, `("USA","PR") == "excluded_location"`, `("USA",None) == "excluded_location"`, `("CAN","ON") == "excluded_location"`.
  - Categories: `("AIR","121","TF","N") → "airliner"`, `("AIR","135","TF","N") → "charter"`, `("HELI","135","TS","N") → "helicopter"`, `("AIR","091","REC","N") → "ga_piston"`, `("AIR","091","TF","N") → "ga_turbine"`, `("AIR","091","REC","Y") → None`, `("GLI","091",None,"N") → None`, `("AIR","129","TF","N") → None`.
  - `is_business_jet("AIR","091","TF") is True`, `("AIR","121","TF") is False`, `("AIR","091","TP") is False`.
  - `test_regions_csv_covers_50_states_plus_dc`: 51 unique states.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. Pre2008 code values may differ in case or padding (e.g., `'91'`), so normalize with strip/upper/zero-pad before matching. Add a test case `("AIR","91","REC","N") → "ga_piston"`.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: region and aircraft category classification`.

### Task 4: Weather-involvement flags across the 2008 coding break

**Files:**
- Create: `data/manual/wx_codes.csv`, `src/rime/ntsb/weather_flags.py`, `scripts/check_coding_break.py`
- Test: `tests/ntsb/test_weather_flags.py`

**Interfaces:**
- Consumes: Task 2 parquet tables.
- Produces: `weather_flags(findings: pd.DataFrame, events_seq: pd.DataFrame, occurrences: pd.DataFrame, seq_of_events: pd.DataFrame) -> pd.DataFrame`, returning one row per `(ev_id, Aircraft_Key)` with bool `wx_involved` and str `wx_basis`, a `;`-joined list of matched codes.

Rules, read from `wx_codes.csv` (`system,table,column,match,code,label,include`):
- **Post-2008 (`avall`):** `Findings.finding_code` starts with `0303` (Environmental issues → Conditions/weather/phenomena), **except** prefix `030360` (light condition), which is excluded.
- **Pre-2008:** `Occurrences.Occurrence_Code` in {`240`, `330`} (in-flight / on-ground encounter with weather), **or** `seq_of_events.Subj_Code` in the weather-condition codes {2202, 2206, 2213, 2224, 2225, 2226, 2227, 2228, 2231, 2233, 2241, 2242, 2243, 2244, 2247, 2253, 2256}.
- **Excluded explicitly** (not weather): 24715 wake turbulence, 410 vortex turbulence.

- [ ] **Step 1: Write failing tests:**
  - `test_post2008_wind_finding_flags`: finding_code `"0303401234"` → `wx_involved` True, basis contains `"0303401234"`.
  - `test_post2008_light_condition_not_weather`: `"0303601234"` → False.
  - `test_pre2008_occurrence_240_flags` and `test_pre2008_subj_icing_flags` (Subj_Code `2213`).
  - `test_wake_turbulence_not_weather` (Subj_Code `24715`).
  - `test_aircraft_without_any_codes_is_false`: an aircraft present in no table → row exists, False.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement, plus a slow real-data test: the share of in-scope accidents flagged `wx_involved` is > 0 in every year 1990–2025.
- [ ] **Step 4:** Write `scripts/check_coding_break.py`. It prints the weather-involved share of all in-scope accidents per year for 2003–2013 and the ratio of mean(2008–2010) to mean(2005–2007). It writes `results/qa/coding_break.csv`. This share isn't split by ENSO, so it's allowed before prereg. If the ratio falls outside 0.67–1.5, stop and report to the user before Task 7. The prereg must then handle the break explicitly (spec §3 sensitivity check).
- [ ] **Step 5:** Run tests and the script. Expected: PASS; CSV written.
- [ ] **Step 6:** Commit `feat: weather-involvement flags with pre/post-2008 crosswalk`.

### Task 5: ONI and ENSO phases

**Files:**
- Create: `src/rime/enso.py`
- Test: `tests/test_enso.py`

**Interfaces:**
- Produces: `ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"` (columns `SEAS YR TOTAL ANOM`; the first row seen 2026-11-02 is `DJF 1950`).
- Produces: `parse_oni(text: str) -> pd.DataFrame` with columns `month` (Timestamp, the center month of the 3-month season: DJF→Jan, …, NDJ→Dec) and `oni` (float = ANOM).
- Produces: `label_phases(oni: pd.DataFrame) -> pd.DataFrame`, which adds `phase` ∈ {`el_nino`, `la_nina`, `neutral`}, `episode_id` (int or NA), `super` (bool: El Niño episode peak ONI ≥ 2.0), and `provisional` (bool).
- Produces: `build_enso() -> None` (CLI step `enso`). Writes `PROCESSED/enso_monthly.parquet`.

The phase rule is NOAA CPC's: a run of ≥5 consecutive seasons with ONI ≥ +0.5 is El Niño; ≤ −0.5 is La Niña; anything else is neutral. A run that touches the end of the record and is shorter than 5 is labeled with its sign's phase and `provisional=True`.

- [ ] **Step 1: Write failing tests** using synthetic series:
  - `test_five_season_run_is_el_nino`: `[0,0.6,0.7,0.8,0.9,0.6,0]` → the middle 5 are `el_nino`, the ends `neutral`.
  - `test_four_season_run_is_neutral`: `[0,0.6,0.7,0.8,0.9,0]` → all `neutral`.
  - `test_super_flag_on_peak_ge_2`: an episode with peak 2.1 → all its months `super=True`; an episode peaking at 1.9 → False.
  - `test_trailing_short_run_is_provisional`: a series ending `[…,0,1.4,1.8,2.2]` → the last 3 are `el_nino`, `provisional=True`, `super=True`.
  - `test_parse_oni_center_month`: line `"  DJF 1950  25.01  -1.32"` → month `1950-01`, oni `-1.32`; `"  NDJ 1950 …"` → `1950-12`.
  - Slow real-file test: months 1997-12 and 2015-12 are `el_nino` and `super`; 2010-12 is `la_nina`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run. Expected: PASS. `uv run rime enso` writes the parquet. Print the latest 6 months and their labels.
- [ ] **Step 5:** Commit `feat: ONI ingest and ENSO phase labeling`.

### Task 6: Annual exposure table

**Files:**
- Create: `data/manual/exposure_annual.csv`, `data/manual/EXPOSURE_SOURCES.md`, `src/rime/exposure.py`
- Test: `tests/test_exposure.py`

**Interfaces:**
- Produces: `load_exposure() -> pd.DataFrame` with columns `year:int, category:str, flight_hours:float, departures:float|NA, source:str, source_url:str`. It validates: categories ∈ the 5 categories; `flight_hours > 0`; no duplicate `(year, category)`.
- Produces: `rate_frame(counts: pd.DataFrame, exposure: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]`, returning `(joined rows with exposure, dropped category-years lacking exposure)`.

Curation, a one-time manual step whose provenance goes in `EXPOSURE_SOURCES.md`, one row per year × category:
- `airliner`: Part 121 flight hours and departures from NTSB's annual "Aviation Data & Stats" tables (FAA-sourced).
- `charter`: Part 135 (scheduled + on-demand) fixed-wing hours. Scheduled hours come from the same NTSB tables. On-demand hours come from the FAA GA and Part 135 Activity Survey.
- `ga_piston`, `ga_turbine`, `helicopter`: FAA GA and Part 135 Activity Survey hours by aircraft type. Rotorcraft includes Part 135 helicopter hours. Piston vs turbine fixed-wing GA excludes Part 135 use. CY2017+ is available as xlsx (e.g., `https://www.faa.gov/data_research/aviation_data_statistics/general_aviation/cy2024/2024GASurveyCh1.xlsx`). For earlier years, transcribe from PDFs.
- **Where a year can't be sourced, leave the row out.** Don't interpolate. The category's study period then starts at its first sourced year, recorded in `EXPOSURE_SOURCES.md`.

- [ ] **Step 1: Write failing tests:**
  - `test_load_exposure_rejects_unknown_category`, `test_load_exposure_rejects_nonpositive_hours`, `test_load_exposure_rejects_duplicates` (all on `tmp_path` CSVs).
  - `test_rate_frame_drops_missing_years`: counts for 1995 and 1996; exposure only for 1996 → joined has 1996; dropped lists `(1995, category)`.
  - `test_committed_exposure_is_valid`: the real CSV loads; every category has ≥ 15 consecutive years ending ≥ 2023.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement the loader, then curate the CSV. Spot-check 3 values per category against their sources and note them in `EXPOSURE_SOURCES.md`.
- [ ] **Step 4:** Run. Expected: PASS.
- [ ] **Step 5:** Commit `feat: annual exposure table with sourced provenance`.

### Task 7: Analysis event table and data-quality report

**Files:**
- Create: `src/rime/ntsb/events.py`, `src/rime/qa.py`
- Test: `tests/ntsb/test_events.py`

**Interfaces:**
- Consumes: Tasks 2–4.
- Produces: `build_events() -> pd.DataFrame` (CLI step `events`). Writes `PROCESSED/events_aircraft.parquet` with one row per in-scope aircraft involvement: `ev_id, Aircraft_Key, ev_date, year, month, ev_type (ACC/INC), highest_injury, fatal (bool), region, category, is_business_jet, dec_latitude, dec_longitude, wx_cond_basic, wx_involved, wx_basis, source_db`. Keeps only US events (`ev_country == 'USA'`), `year >= 1990`, and in-scope categories. The ONI/phase is **not** joined here.
- Produces: `counts_by_category_year(events: pd.DataFrame) -> pd.DataFrame` with columns `year, category, accidents, wx_accidents, fatal_accidents, fatal_wx_accidents` (ACC only). This is the **only** outcome summary allowed before prereg.
- Produces: `qa_report() -> None` (CLI step `qa`). Writes `results/qa/data_quality.md` with: rows dropped by reason (out-of-scope category, excluded_location, pre-1990, non-US), missing coordinates share by year, and `counts_by_category_year` as a table.

- [ ] **Step 1: Write failing tests:**
  - `test_midair_two_aircraft_two_rows`: one event with an `airliner` and a `ga_piston` → 2 rows; `counts_by_category_year` gives 1 accident in each category.
  - `test_excluded_location_dropped_and_reported`: an event with state `PR` is absent from output and counted in the drop reasons.
  - `test_no_enso_columns_before_prereg`: the output has no column matching `oni|phase|enso`.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement. Register `events` and `qa` in the CLI after `ntsb`, `enso`.
- [ ] **Step 4:** Run tests, then `uv run rime all`. Expected: PASS; `results/qa/data_quality.md` written.
- [ ] **Step 5:** Commit `feat: analysis event table and data-quality report`.

### Task 8: Power analysis

**Files:**
- Create: `src/rime/power.py`
- Test: `tests/test_power.py`

**Interfaces:**
- Consumes: `counts_by_category_year`, `enso_monthly.parquet` (covariate only), `load_exposure`.
- Produces: `simulate_power(monthly_mean: float, dispersion: float, phases: pd.Series, rate_ratio: float, alpha: float, n_sims: int, rng: np.random.Generator) -> float`.
- Produces: `minimal_detectable_rr(...) -> float | None`: the smallest RR on grid `1.05, 1.10, …, 2.00` with power ≥ 0.80, or None if none qualifies.
- Produces: `run_power() -> None` (CLI step `power`). Writes `results/power/mdrr.csv` with columns `category, years, total_wx_accidents, monthly_mean, dispersion, mdrr_el_nino, mdrr_la_nina`.

Method:
- The simulated monthly weather-involved counts per category are NegBin with mean `monthly_mean × seasonal_profile[m] × RR^{1[phase=target]}`.
- `phases` is the real historical monthly ENSO sequence over the category's study period.
- `seasonal_profile` is flat (1.0). Seasonality isn't estimated, because that would need monthly outcome data, which is allowed but unnecessary here.
- `dispersion` is the method-of-moments estimate from **annual** weather-involved counts per category, after removing a linear trend.
- Each simulation fits a statsmodels NB GLM (`count ~ C(phase) + trend`) and tests the target phase coefficient.
- `alpha = 0.05 / 10` (5 categories × 2 phases). `n_sims = 500`; seed `20261102`.

- [ ] **Step 1: Write failing tests:**
  - `test_power_increases_with_rr`: power(RR=1.5) > power(RR=1.1) with monthly_mean 20.
  - `test_power_near_alpha_at_null`: RR=1.0, n_sims 400 → power < 0.03.
  - `test_mdrr_none_when_too_rare`: monthly_mean 0.05 → None.
- [ ] **Step 2:** Run. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run tests, then `uv run rime power`. Expected: PASS; `mdrr.csv` written. Report the table to the user in plain words ("for airliners we could only detect a ≥X% change").
- [ ] **Step 5:** Commit `feat: power analysis for ENSO effects by category`.

### Task 9: Pre-registration draft → user approval → lock

**Files:**
- Create: `prereg/hypotheses.md`

**Interfaces:**
- Consumes: `results/power/mdrr.csv`, `results/qa/coding_break.csv`, spec §3.

- [ ] **Step 1:** Draft `prereg/hypotheses.md`. For each of H1, H2, and H3 it states:
  - the exact outcome (weather-involved accidents, and fatal subset)
  - the categories tested (drop any whose `mdrr_el_nino` is None or > 2.0, saying why)
  - the regions and seasons, with the expected sign per region-season for H1 from NOAA's published US ENSO impacts (cite them)
  - the ENSO lag (0 and 3 months, primary = 0)
  - the model formula: NB GLM, `log(flight_hours)` offset, month-of-year fixed effects, linear + quadratic year trend, `C(phase)`. Exposure is annual and national, so monthly models use `flight_hours / 12`. Regional models add region fixed effects and assume each region's traffic share is constant within a year. The prereg states that assumption as a limitation.
  - the multiple-comparison correction (Holm across the confirmatory family) and α = 0.05
  - the 2008 coding-break handling (from Task 4's result)
  - sensitivity analyses
  - H2/H3 hazard metrics, defined precisely as the ERA5 variables, levels, and thresholds Plan 2 will compute
  - what counts as "no relationship"
  Everything else is labeled exploratory.
- [ ] **Step 2:** Self-check against the spec's anti-goals (fishing, raw counts, hiding a null). Commit `docs: draft pre-registration`.
- [ ] **Step 3: STOP. Present the prereg to the user in plain language and wait for explicit approval.** Apply requested changes and re-present. Don't proceed without approval.
- [ ] **Step 4:** After approval: `gh repo create rime --public --source . --push`, and push `main` + `plan1-foundation`. Merge `plan1-foundation` into `main` via PR, then `git tag -a prereg-v1 -m "rime pre-registration v1"` on the merge commit and `git push origin prereg-v1`. Record the tag's commit SHA and date at the top of `prereg/hypotheses.md` in a follow-up commit.
