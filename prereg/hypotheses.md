# rime pre-registration (Part 1)

**Status: DRAFT, not locked.** It locks when the user approves it and it's tagged `prereg-v1`. The tag's commit SHA and date get recorded here after locking.

## What this document does

It fixes, before any outcome is split by El Niño phase, region-season, or hazard type:
- which tests count as **confirmatory**
- exactly how each is computed
- what counts as "no relationship"

Anything not listed here is reported as **exploratory**.

Before writing this, the only outcome data computed was accident counts per aircraft category per year (`results/qa/data_quality.md`) and the weather-involved share per year around the 2008 coding change (`results/qa/coding_break.csv`). Neither is split by ENSO, region, season, or hazard.

## 1. Data and scope

- **Accidents:** the NTSB aviation accident database (`avall.mdb` + `Pre2008.mdb`), downloaded 2026-11-02. Checksums are in `data/raw/MANIFEST.json`, and the lock commit records them.
- Only `ev_type = ACC`, except H3, which also uses incidents.
- **Scope:** US, the 9 NCEI climate regions plus Alaska and Hawaii. Unit = one aircraft involvement.
- **Categories:** `airliner`, `charter`, `ga_piston`, `ga_turbine`, `helicopter` (rules in `src/rime/ntsb/classify.py`).
- **Study period:** 1990–2024, limited per category to the years with sourced exposure (see the power table).
  - 2025 onward is excluded because NTSB is still entering those cases. For example, 2025 shows 590 GA piston accidents against about 880 a year normally.
  - The FAA ran no GA survey for 2011, so 2011 is excluded for survey-based categories.
- **Weather-involved:** defined in `data/manual/wx_codes.csv`.
  - 2008 onward: NTSB findings `0303*`, excluding light condition and wake turbulence.
  - Before 2008: subject 20000 "weather condition", plus occurrence codes 240 and 330.
- **Exposure:** annual national flight hours per category (`data/manual/exposure_annual.csv`, sources in `EXPOSURE_SOURCES.md`).
- **ENSO:** NOAA CPC ONI, using CPC's rule: ≥5 consecutive overlapping seasons at ≥ +0.5 is El Niño, ≤ −0.5 is La Niña. Each season is assigned to its center month.
  - The ONI file used is frozen at lock as `data/manual/oni_snapshot.txt`, because CPC revises recent values.
  - Months labeled provisional are excluded (none fall inside the study period).

## 2. Statistical model (shared by H1)

The model is a negative binomial GLM (log link) on **monthly** counts of weather-involved accidents, per category:

```
count_m ~ C(phase_m) + C(month_of_year_m) + year + year² , offset = log(flight_hours_year / 12)
```

- `phase` ∈ {neutral (reference), el_nino, la_nina}, at lag 0. The NB dispersion is estimated by maximum likelihood.
- Effects are reported as rate ratios (RR) with 95% CIs.
- **Exposure is annual and national.** Monthly models therefore spread each year's hours evenly across its months.
- Regional models (H1-R) count accidents only in the region group, with the same national offset. This assumes the region group's share of national traffic changes only slowly; the year terms absorb slow change. That's a stated limitation.

## 3. Confirmatory hypotheses

Power results (from `results/power/mdrr.csv`) decide which categories enter each family:

| Category | Primary period | Weather-involved accidents | MDRR El Niño | MDRR La Niña |
|---|---|---|---|---|
| airliner | 1997–2024 (28 yrs) | 304 | 1.65 | 1.65 |
| charter | 2004–2024 (20 yrs, no 2011) | 189 | 1.75 | 1.80 |
| ga_piston | 2004–2024 (20 yrs, no 2011) | 4,498 | 1.25 | 1.25 |
| ga_turbine | 2004–2024 (20 yrs, no 2011) | 286 | 1.95 | 1.95 |
| helicopter | 2004–2024 (20 yrs, no 2011) | 443 | 1.45 | 1.50 |

MDRR is at 80% power with α = 0.05/10, from 500 simulations per grid point (seed 20261102). See `src/rime/power.py`.

**Primary periods start after exposure-definition breaks:**
- In March 1997, scheduled commuter operations with 10 or more seats moved from Part 135 to Part 121.
- In 2004, FAA redesigned its GA/Part 135 activity survey.
- The longer spans that have sourced exposure (airliner 1992+, GA and helicopter 1999+) are run as sensitivity analysis 7.

A category is tested in a family only if its minimal detectable rate ratio (MDRR, at 80% power and the family's Bonferroni-equivalent α) is ≤ 2.0. Excluded categories are reported descriptively, with the reason.

### H1-N: national ENSO effect (two-sided)
For each eligible category, the weather-involved accident rate differs between El Niño and neutral months, and between La Niña and neutral months. That's up to 10 tests, Holm-corrected, family-wise α = 0.05.

### H1-R: regional winter effects (directional, one-sided)
Winter here is November–March, the ENSO-teleconnection season. The predicted directions come from NOAA's published US winter ENSO impacts (Climate Prediction Center ENSO composites, and NOAA Climate.gov "How El Niño and La Niña affect the winter jet stream and U.S. climate"):
- **H1-Ra:** In El Niño winters, the rate is *higher* in the **southern tier** (southeast, south, southwest, west), where the stronger, more southerly jet brings more storms and precipitation.
- **H1-Rb:** In La Niña winters, the rate is *higher* in the **northern tier** (northwest, northern_rockies_plains, upper_midwest, ohio_valley), which gets wetter and colder with more snow.

Regional winter subsets hold roughly a fifth of a category's events. Only `ga_piston` (national MDRR 1.25) has enough events for this, so **H1-R is confirmatory for `ga_piston` only** (2 tests). For other categories it's exploratory. Test: one-sided Wald test on the phase coefficient, winter months only, Holm across the 2 tests, α = 0.05.

### H2: hazard trends and their link to hazard-specific accidents
Three hazards. Each is defined on the accident side by codes, and on the weather side by an ERA5 index. Plan 2 computes the index over the contiguous US at 0.25°, 6-hourly (00/06/12/18 UTC), 1990–2024.

| Hazard | Accident codes (2008 onward / before 2008) | ERA5 annual index: share of CONUS grid-times where… |
|---|---|---|
| Structural icing | finding `03031025` / subject 20000 + modifier 2213 | some pressure level 850–400 hPa has −20 °C ≤ T ≤ 0 °C, RH ≥ 85%, and specific cloud liquid water ≥ 0.01 g/kg |
| Turbulence (non-wake) | findings `030320*` except `03032025` / modifiers 2224, 2225, 2226, 2227, 2253, 2256 | Ellrod TI1 in the 300–200 hPa layer ≥ 8×10⁻⁷ s⁻² |
| Convective | findings `030330*` and `03034050` microburst / modifiers 2228, 2241, 2242, 2243, 2244 | CAPE ≥ 1000 J/kg and 6-hour convective precipitation ≥ 1 mm |

- **H2a (trend):** each annual index has a non-zero linear trend over 1990–2024. That's 3 tests: OLS with Newey–West (lag 2) standard errors.
- **H2b (link):** for each eligible category, the annual hazard-specific accident count rises with the standardized annual index:

  ```
  NB GLM: count_y ~ index_y + year + year², offset log(flight_hours_y)
  ```

  It's one-sided (positive). A hazard × category pair is tested only if it has ≥ 30 events over the period.
- H2a and H2b are separate Holm families, α = 0.05 each.

### H3: high-altitude convective / ice-crystal events
- **Outcome:** accidents *and incidents* in turbine categories (`airliner`, `charter`, `ga_turbine`) with icing, turbulence, or convective codes, during cruise / climb / descent.
- **Index:** the share of CONUS grid-times with CAPE ≥ 1500 J/kg *and* specific cloud ice water ≥ 0.05 g/kg at 300 or 250 hPa.
- **Hypotheses:**
  - **H3a:** the index has a positive linear trend.
  - **H3b:** the annual outcome count rises with the index (same model form as H2b).
- If fewer than 20 qualifying events exist, H3b is reported descriptively and marked underpowered, not tested.

## 4. "No relationship" criterion

A confirmatory test that isn't significant after correction is reported as "no detectable relationship." The report states the largest effect the data rule out: the upper 95% CI bound of the RR, as "an effect larger than X is unlikely."

A null result is the headline when it's the result.

## 5. Coding break (2008)

The weather-involved share changes smoothly across the switch. The ratio of 2008–10 to 2005–07 is 0.94 (`results/qa/coding_break.csv`), so the primary models get no adjustment. A sensitivity check adds a post-2008 indicator.

## 6. Pre-specified sensitivity analyses (reported alongside, not confirmatory)

1. ENSO at a 3-month lag.
2. A post-2008 coding indicator added.
3. Fatal weather-involved accidents only.
4. Alaska and Hawaii excluded from national models.
5. **Negative control:** the same H1-N models on *non*-weather accidents. ENSO shouldn't affect these; if it does, the H1-N results may reflect confounding, and the report must say so.
6. Super El Niño months (episode peak ONI ≥ 2.0) as a separate phase level.
7. Full exposure spans (airliner 1992–2024; GA and helicopter 1999–2024), with indicators for pre-1997 (airliner) and pre-2004 (GA, helicopter).

## 7. Exploratory (labeled as such)

Everything else, including:
- individual regions rather than the tiers
- other seasons, including the hurricane season (Aug–Oct)
- other hazards (wind, ceiling/visibility)
- individual-event case studies
- ASRS reports
- the Part 2 cross-reference
