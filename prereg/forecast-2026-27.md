# rime out-of-sample forecast: the 2026–27 super El Niño

**Status: DRAFT, not locked.** It locks when the author approves it and it's tagged `forecast-2026-27`. It must be locked before any NTSB accident data for the forecast window is analyzed. It must also be locked before 2026-12-01, so the prediction comes before most of the winter it covers.

## Why

`prereg-v1` tested ENSO effects on 1997–2024 data. The 2026–27 event is a super El Niño: ONI reached +2.16 in Jul–Sep 2026, per the pinned snapshot. Writing down now what the historical results predict, then checking it once the data exists, gives a genuine out-of-sample test that can't be fitted after the fact.

## What the historical data say (from `results/h1/`, run at tag `prereg-v1`)

- **Private piston planes (ga_piston), super El Niño months vs neutral months, within-year model (sensitivity 6):** RR 0.99, 95% CI 0.84–1.16, based on 4,628 weather-involved accidents in 2004–2024.
- **Southern-tier share of ga_piston weather accidents in El Niño winters (H1-Ra):** odds ratio 1.18, 95% CI 0.90–1.55. Not significant.

## Predictions (fixed now)

**F1 (national):** for ga_piston, the weather-involved accident rate in super El Niño months of the 2026–27 episode, relative to neutral months in the same calendar years, will fall inside the historical 95% CI **0.84–1.16**.
- Model: the H1-N model (year + month-of-year fixed effects, NB), fitted on 2025–2027 months only, with the phase from the ONI as published at analysis time.
- Falsified if the forecast-window RR's 95% CI lies entirely outside 0.84–1.16.

**F2 (regional winter):** in the 2026–27 winter (Nov 2026–Mar 2027), the southern tier's share of ga_piston weather-involved accidents will be inside the range the historical neutral-winter share and H1-Ra's CI imply. The comparison is the share in Nov 2026–Mar 2027 against the mean share in neutral winters 2004–2024, using the H1-R binomial model with that winter as the El Niño level.
- Falsified if the odds-ratio 95% CI lies entirely outside 0.90–1.55.

Other categories are too sparse for a single-winter test, so they're reported descriptively only.

## When and how it's checked

- Not before NTSB's data for 2027 is substantially complete (the 2025 coverage pattern suggests about 18 months after year end, so around mid-2029). The check uses the then-current `avall.mdb`, recording its sha256.
- The same code paths as `rime h1`, with only the year window changed. Any change to code beyond the window is reported.
- Either outcome is reported: "confirmed" means super El Niño again made no detectable difference, and "falsified" is reported with the numbers.
