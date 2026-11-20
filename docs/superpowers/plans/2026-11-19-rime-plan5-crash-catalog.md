# rime Plan 5: Part 2 crash catalog

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the spec §4a crash catalog, "there was a crash and this is what happened". It holds the physical facts of every serious US accident 1990–2024, kept separate from any weather or investigative conclusion and ready for the §4c cross-reference. Write it to `data/processed/crash_catalog.parquet`, with a coverage and quality report in `results/catalog/summary.md`.

**Architecture:** New subpackage `rime.catalog`:
- `timecheck.py`: solar elevation, and day/night consistency against NTSB's `light_cond`.
- `altitude.py`: conservative extraction of the event altitude from the factual narrative, keeping the source span.
- `build.py`: CLI step `crashes`, which assembles the catalog and writes the report.

**Tech Stack:** existing (pandas, numpy). No new dependencies: the solar position uses the NOAA approximation.

**Spec:** `docs/superpowers/specs/2026-11-02-rime-design.md` §4a and its "where is the line" ruling. Allowed: physical facts from structured fields, occurrence codes describing what the aircraft did, and time/altitude from the factual narrative. Excluded: probable cause, contributing factors, findings, and investigator-attributed weather.

## Global Constraints

- **Scope:** `events_aircraft.parquet` rows with `ev_type == "ACC"`, `highest_injury ∈ {FATL, SERS}`, and year 1990–2024 (16,431 aircraft rows). Incidents are deferred, because their reporting changed over time (see the prereg H3 note).
- **Columns:**
  - `ev_id, Aircraft_Key, ntsb_no, time_utc` (Timestamp or NaT)
  - `time_flag` ∈ {`ok`, `no_time`, `daynight_mismatch`}
  - `lat, lon, region, category, is_business_jet, highest_injury, fatal`
  - `phase` (harmonized: `standing|taxi|takeoff|climb|cruise|descent|approach|landing|maneuvering|other|unknown`)
  - `defining_event` (text), `altitude_ft` (float or NaN), `altitude_ref` ∈ {`msl`, `agl`, `fl`, `unspecified`, ``}, `altitude_span` (≤ 160 chars of narrative, or empty)
  - `source_db`
- **Must not appear:** any `wx_*` column, findings, cause text, or `narr_cause`. A test enforces this.
- **Time:** NTSB `ev_date` + `ev_time` (HHMM), as stored. `ev_tmzn` is "UTC" for 98% of rows; trust it, and verify with the day/night check. Rows where `ev_tmzn` isn't UTC get `time_flag = no_time` (we don't guess zones).
- **Day/night check:**
  - Compute the solar elevation at (lat, lon, time_utc).
  - NTSB `light_cond` (from `events`): `DAYL` (day), `NITE`/`NDRK`/`NBRT` (night), `DUSK`/`DAWN` (twilight).
  - A mismatch is `DAYL` with elevation < −6°, or a `NITE*` code with elevation > +6°. Twilight codes and missing values are never mismatches.
- **Phase:**
  - Post-2008: the phase prefix of the `Events_Sequence` row with `Defining_ev == True`.
  - Pre-2008: the `Phase_of_Flight` of the aircraft's first occurrence (`Occurrence_No` = 1).
  - The mapping is in `data/manual/phase_map.csv` (code → harmonized phase), covering every 3-digit post-2008 prefix and every pre-2008 phase code seen.
  - `defining_event`: post-2008 the defining row's `Occurrence_Description`; pre-2008 the first occurrence's code meaning from `ct_seqevt`.
- **Altitude extraction:** from `narr_accf` (else `narr_accp`). Only these patterns, case-insensitive, first match wins, in this order:
  1. `FL ?(\d{3})` or `flight level (\d{3})` → ×100, ref `fl`
  2. `(?:altitude|cruise|cruising|level(?:ed)? (?:off )?at)\D{0,40}?(\d{1,2},?\d{3}) (?:feet|ft)( msl| agl)?`
  3. `(\d{1,2},?\d{3}) (?:feet|ft) (msl|agl)`
  - Values outside 100–51,000 ft are rejected.
  - Mentions of runway, elevation (field/airport elevation), visibility, or ceiling within 30 characters before the number are rejected.
  - Store the matched span with up to 60 characters of context on each side.
  - This is deliberately conservative: precision over coverage.

## Review Focus

1. **Midnight and date rollover:** `ev_time` 2350 on 12-31 must stay that day, while 0005 is the next calendar day only if NTSB stored it that way. Construct the time from `ev_date` + HHMM literally, with no shifting. Test in Task 3.
2. **Invalid HHMM** (e.g. 2460, 975): `time_flag = no_time`, never an exception. Test in Task 3.
3. **Narrative numbers that aren't flight altitude** (runway 5,000 ft, field elevation 6,500 ft, visibility, ceiling): rejected. Test in Task 2.
4. **Aircraft with no defining event or occurrence:** phase `unknown`, defining_event empty, row kept. Test in Task 3.
5. **Polar/edge cases in solar elevation** (Alaska in winter, the dateline doesn't apply to the US): the formula must stay finite; NaN lat/lon gives NaN elevation, which is never a mismatch. Test in Task 1.

---

### Task 1: Solar elevation and day/night check

**Files:** Create `src/rime/catalog/__init__.py`, `src/rime/catalog/timecheck.py`; Test `tests/catalog/test_timecheck.py`

**Interfaces:**
- `solar_elevation_deg(lat, lon, time_utc) -> ndarray` (NOAA general solar position approximation)
- `daynight_mismatch(elev_deg, light_cond) -> ndarray[bool]`

- [ ] **Step 1: Write failing tests:**
  - Solar noon at the equinox (2020-03-20 12:00 UTC, lat 0, lon 0) → elevation 88–90°.
  - Midnight (2020-06-21 00:00 UTC at lat 40, lon 0) → < −20°.
  - Kobe (34.14, −118.70, 2020-01-26 17:45 UTC) → between 20 and 40°.
  - NaN lat → NaN.
  - Mismatch: `DAYL` at −10° → True; `DAYL` at −3° → False; `NITE` at 20° → True; `DUSK` at 20° → False; None at −10° → False.
- [ ] **Steps 2–5:** FAIL, implement, PASS, commit `feat(catalog): solar elevation and day/night check`.

### Task 2: Narrative altitude extraction

**Files:** Create `src/rime/catalog/altitude.py`; Test `tests/catalog/test_altitude.py`

**Interfaces:** `extract_altitude(text: str | None) -> tuple[float, str, str]`, returning (`altitude_ft` or NaN, `ref`, `span`).

- [ ] **Step 1: Write failing tests** (one per case):
  - "cruising at FL350 when" → (35000, "fl")
  - "at an altitude of about 2,500 feet msl" → (2500, "msl")
  - "descended through 11,000 ft agl" → (11000, "agl")
  - "the 5,000-foot runway" → NaN
  - "field elevation 6,500 feet msl" → NaN
  - "visibility of 1,500 feet" → NaN
  - "an altitude of 75,000 feet" → NaN (out of range)
  - None → NaN
  - The span contains the matched text.
- [ ] **Steps 2–5:** FAIL, implement, PASS, commit `feat(catalog): conservative narrative altitude extraction`.

### Task 3: Catalog builder and report

**Files:** Create `src/rime/catalog/build.py`, `data/manual/phase_map.csv`; register the CLI `crashes`; Test `tests/catalog/test_build.py`

**Interfaces:**
- `harmonize_phase(post_prefix: int | None, pre_code: int | None) -> str`
- `build_catalog(events_aircraft, events, events_seq, occurrences, narratives, ct_seqevt) -> pd.DataFrame`
- `render_summary(cat) -> str`, with coverage per column per decade and per category, time_flag counts, the altitude extraction rate, and 10 random altitude spans for spot checking (seed 20261102).
- `run_crashes()` (CLI step `crashes`, in `all`): writes the parquet and `results/catalog/summary.md`.

- [ ] **Step 1: Write failing tests** (synthetic frames):
  - Literal time: 2005-12-31 with 2350 → 2005-12-31 23:50.
  - Invalid 2460 → NaT, `no_time`.
  - A non-UTC `ev_tmzn` → `no_time`.
  - Post-2008 defining event row `402240` → phase `cruise`, with defining_event taken from its description.
  - A pre-2008 first occurrence with phase 541 → `cruise`.
  - No occurrences → `unknown`, row kept.
  - Forbidden columns are absent: no column matching `wx_|finding|cause`.
  - Only FATL/SERS ACC rows from 1990–2024 are present.
- [ ] **Step 2:** FAIL. **Step 3:** Build `phase_map.csv` from the distinct codes observed (pre-2008 data dictionary + post-2008 prefixes), then implement. **Step 4:** PASS, then `uv run rime crashes`. Read the summary and check that the day/night mismatch rate is reported per decade. Spot-check the 10 altitude spans by reading them. If more than 2 of 10 are wrong, tighten the patterns and record a ruling.
- [ ] **Step 5:** Commit `feat(catalog): Part 2 crash catalog`.
