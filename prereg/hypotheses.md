# rime pre-registration (Part 1)

**Status: LOCKED.** Approved by the author and tagged `prereg-v1` on 2026-11-02, at commit `18299e7dc71d7894ccd9b7b36ee050436ef8edb3`. To check that nothing confirmatory changed afterward, run `git diff prereg-v1 -- prereg/hypotheses.md`. The only post-lock edit is this status line.

## What this document does

It fixes, before any outcome is split by El Niño phase, region-season, or hazard type:
- which tests count as **confirmatory**
- exactly how each is computed
- what counts as "no relationship"

Anything not listed here is reported as **exploratory**.

Before writing this, the only outcome data computed was:
- accident counts per aircraft category per year (`results/qa/data_quality.md`)
- the weather-involved share per year around the 2008 coding change (`results/qa/coding_break.csv`)

Neither is split by ENSO, region, season, or hazard.

## 1. Data, scope, and pinned versions

- **Accidents:** the NTSB aviation accident database (`avall.mdb` + `Pre2008.mdb`). Only `ev_type = ACC` (accidents) is used, never incidents.
  - Unit: one aircraft involvement in the US, assigned to one of the 9 NCEI climate regions, Alaska, or Hawaii.
  - "Fatal" means the event's highest injury is fatal.
- **Pinned inputs:** sha256 and retrieval dates for every downloaded file are in `data/manual/data_versions.json`.
  - NTSB re-publishes its database monthly and keeps no archive. A fresh run prints a warning when its download differs from the pinned version.
  - The ONI used is the committed snapshot `data/manual/oni_snapshot.txt`, retrieved 2026-11-02.
- **Categories:** `airliner` (Part 121), `charter` (Part 135 fixed-wing), `ga_piston` and `ga_turbine` (Parts 91/125/133/137 fixed-wing), and `helicopter` (Parts 91/125/133/135/137).
  - Public-use, military, foreign, and other operations are excluded for every category.
  - The rules are in `src/rime/ntsb/classify.py`.
- **Primary study period, per category:**
  - airliner: **1997–2024**
  - all others: **2004–2024 without 2011**
  - The starts follow breaks in exposure definitions: the 1997 commuter rule moved 10+ seat scheduled flying from Part 135 to Part 121, and FAA redesigned its activity survey in 2004.
  - 2025 onward is excluded because NTSB is still entering those cases (2025 GA piston: 590 accidents against about 880 a year normally).
  - FAA ran no survey for 2011.
- **Weather-involved:** defined in `data/manual/wx_codes.csv`. The 2008-onward and pre-2008 coding systems are harmonized as follows.

  | | 2008 onward | Before 2008 |
  |---|---|---|
  | Weather findings / subjects | findings `0303*`, except light condition `030360` and wake turbulence `03032025` | subject 20000 "weather condition" with a weather modifier 2200–2299 |
  | Weather occurrences | 210 structural icing, 360 turbulence, 362 clear-air turbulence, 390 windshear/thunderstorm, 400 other weather, 401 VFR into IMC (the last 3 digits of the Events_Sequence code) | 240, 330 (weather encounter) |
  | Excluded | wake turbulence occurrence 361 | wake turbulence 24715 / 410 |

  The weather-involved share changes smoothly across the switch. The ratio of 2008–10 to 2005–07 is 0.96 (`results/qa/coding_break.csv`).
- **Exposure:** annual national flight hours per category (`data/manual/exposure_annual.csv`, sources in `EXPOSURE_SOURCES.md`).
- **ENSO:** NOAA CPC ONI, assigned to each 3-month season's center month and **rounded to 0.1 before thresholds**, as CPC does.
  - El Niño: ≥5 consecutive seasons at ≥ +0.5. La Niña: ≥5 consecutive seasons at ≤ −0.5.
  - Super El Niño: an episode peak ≥ 2.0. The 1997–98, 2015–16, and 2023–24 episodes qualify.
  - Primary lag: 0.

## 2. Why the design compares months within the same year

Monthly accident counts aren't independent across months.
- ENSO phases persist for many months.
- Exposure is known only per year, so any error in a year's hours is shared by all its months.

In simulation, a model that treats months as independent gave **false positives about 10× too often** (25% where 2.5% was intended) once realistic year-level variation was present. Cluster-robust standard errors with about 20 years also over-rejected, giving about 3×. That's why the confirmatory H1 tests compare months **within the same year**:

```
H1-N (per category):  NB GLM, monthly weather-involved accidents
    count[y,m] ~ C(phase[y,m]) + C(year) + C(month_of_year)
```

- Year fixed effects absorb anything shared by a year's months: exposure level and its errors, the long-run safety trend, and other year-level shocks. A flight-hours offset would therefore be absorbed and is unnecessary.
- The ENSO rate ratio comes from months in the same year that sit in different ENSO phases, compared after removing normal seasonality.
- NB dispersion is estimated by maximum likelihood, with model-based SEs and a Wald test.
- Simulated false-positive rate under year-level variation: 3–3.5% at a one-sided nominal 2.5% (`tests/test_power.py`). That's within simulation noise.

```
H1-R (ga_piston, winter Nov–Mar):  binomial GLM of the region tier's share
    (tier_count[s,m], rest_count[s,m]) ~ C(phase[s,m])
```

- The model is fit on winter months; `s` is the winter season.
- A phase usually lasts the whole winter, so a within-winter comparison has no contrast to measure. The tier's *share* of national weather accidents is used instead. Shocks common to the whole country, including exposure errors, cancel in a share.

## 3. Confirmatory hypotheses

### Power (`results/power/mdrr.csv`, seed 20261102, 500 simulations per grid point)

| Family | Category | Period | Weather-involved accidents | MDRR El Niño | MDRR La Niña |
|---|---|---|---|---|---|
| H1-N | airliner | 1997–2024 | 308 | 1.75 | 1.80 |
| H1-N | charter | 2004–2024 | 195 | 1.95 | > 2.0 |
| H1-N | ga_piston | 2004–2024 | 4,628 | 1.20 | 1.20 |
| H1-N | ga_turbine | 2004–2024 | 295 | 1.75 | 1.80 |
| H1-N | helicopter | 2004–2024 | 428 | 1.60 | 1.70 |
| H1-R | ga_piston (tier share 0.40 / pessimistic 0.20) | winters 2004–2024 | — | 1.40 / 1.50 | 1.40 / 1.45 |

- MDRR is the smallest rate ratio detectable with 80% power.
- H1-N uses α = 0.005 per test (0.05/10). H1-R uses one-sided α = 0.025.
- Tier shares are *assumed*, not computed from outcomes: each tier covers 4 of the 9 CONUS regions.
- The power simulation uses flat seasonality and Poisson month noise around gamma year effects, which is a simplification of the fitted models.
- **Family membership is fixed by this table.** Tests with MDRR ≤ 2.0 are confirmatory. **charter × La Niña** (MDRR > 2.0) is reported as exploratory.

### H1-N: national ENSO effect (two-sided)
For each category, the weather-involved accident rate differs between El Niño and neutral months, and between La Niña and neutral months, using the §2 model.
- 9 tests (all 10 pairs except charter × La Niña), Holm-corrected, family-wise α = 0.05.
- Results are reported as RR with 95% CI.

### H1-R: regional winter effects (directional, one-sided; ga_piston only)
The predicted directions come from NOAA's published US winter ENSO impacts: the CPC ENSO composites, and NOAA Climate.gov, "How El Niño and La Niña affect the winter jet stream and U.S. climate".
- **H1-Ra:** In El Niño winters, the **southern tier** (southeast, south, southwest, west) has a *larger* share of weather-involved accidents.
- **H1-Rb:** In La Niña winters, the **northern tier** (northwest, northern_rockies_plains, upper_midwest, ohio_valley) has a *larger* share.

Each is a one-sided Wald test, Holm across the 2 tests, α = 0.05. Other categories are exploratory, because their winter regional counts are too small.

### H2: hazard trends and their link to hazard-specific accidents
Three hazards. Each is defined on the accident side by codes, and on the weather side by an ERA5 index. Plan 2 computes the index over the contiguous US at 0.25°, 6-hourly (00/06/12/18 UTC), over each category's primary period.

| Hazard | Accident codes, 2008 onward (findings; occurrences) | Accident codes, before 2008 (subject-20000 modifiers) | ERA5 annual index: share of CONUS grid-times where… |
|---|---|---|---|
| Structural icing | `03031025`; occ 210 | 2213 | some level 850–400 hPa has −20 °C ≤ T ≤ 0 °C, RH ≥ 85%, and specific cloud liquid water ≥ 0.01 g/kg |
| Turbulence (non-wake) | `030320*` except `03032025`; occ 360, 362 | 2224, 2225, 2226, 2227, 2253, 2256 | Ellrod TI1 in the 300–200 hPa layer ≥ 8×10⁻⁷ s⁻² |
| Convective | `030330*` (thunderstorm, lightning, hail), `03034050` microburst; occ 390 | 2208 hail, 2215 lightning, 2216 lightning strike, 2228 thunderstorm, 2238/2239 microburst, 2241–2244 thunderstorm levels / outflow | CAPE ≥ 1000 J/kg and 6-hour convective precipitation ≥ 1 mm |

- **H2a (trend):** each annual index has a non-zero linear trend, 1990–2024. That's 3 tests: OLS with Newey–West (lag 2) standard errors.
- **H2b (link):** for each category, the annual count of hazard-specific accidents rises with the standardized annual index:

  ```
  NB GLM: count_y ~ index_y + year + year², offset log(flight_hours_y), primary period
  ```

  It's one-sided (positive). A hazard × category pair is tested only if it has ≥ 30 events in its primary period. That count is computed at analysis time, and pairs below it are reported descriptively.
- **Per-hazard 2008 break check (run after lock, before H2b):** if a hazard's share of weather-involved accidents changes across 2008 by a factor outside 0.67–1.5 (mean of 2008–10 over mean of 2005–07), H2b for that hazard adds a post-2008 indicator, and the report says so.
- H2a and H2b are separate Holm families, α = 0.05 each.

### H3: high-altitude convective / ice-crystal events
- **Outcome:** accidents (not incidents, whose reporting changed a lot over time) in `airliner`, `charter`, and `ga_turbine` with icing, turbulence, or convective codes, in cruise, climb, or descent.
  - Phase of flight comes from Occurrences.Phase_of_Flight before 2008, and from the first 3 digits of the Events_Sequence code (en-route codes 4xx) from 2008 on. Plan 2 commits the crosswalk before running H3.
- **Index:** the share of CONUS grid-times with CAPE ≥ 1500 J/kg *and* specific cloud ice water ≥ 0.05 g/kg at 300 or 250 hPa.
- **Hypotheses:**
  - **H3a:** the index has a positive linear trend.
  - **H3b:** the annual outcome count rises with the index (same model form as H2b, period 2004–2024).
- If fewer than 20 qualifying events exist, H3b is reported descriptively and marked underpowered, not tested.

### Across families
Each family controls its own error rate. There's **no** correction across families, and the report says so.

## 4. "No relationship" criterion

A confirmatory test that isn't significant after correction is reported as "no detectable relationship." The report gives the **full 95% CI** for the RR and the range of effects it rules out, in both directions where the test was two-sided.

A null result is the headline when it's the result.

## 5. Pre-specified sensitivity analyses (reported alongside, not confirmatory)

1. ENSO at a 3-month lag.
2. A post-2008 coding indicator (H2b/H3b).
3. Fatal weather-involved accidents only.
4. Alaska and Hawaii excluded from national models.
5. **Negative control:** the same H1-N models on *non*-weather accidents. ENSO shouldn't affect these; if it does, H1-N may reflect confounding, and the report must say so.
6. Super El Niño months as a separate phase level.
7. Full exposure spans (airliner 1992–2024; GA and helicopter 1999–2024).
8. H1-N as an NB GLM with linear + quadratic year trends, a `log(flight_hours/12)` offset, and standard errors clustered by year. This is the originally drafted model, kept for comparison.

## 6. Exploratory (labeled as such)

Everything else, including:
- individual regions rather than the tiers
- other seasons, including the hurricane season (Aug–Oct)
- other hazards (wind, ceiling/visibility)
- incidents
- individual-event case studies
- ASRS reports
- the Part 2 cross-reference
