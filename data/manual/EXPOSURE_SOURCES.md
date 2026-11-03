# Exposure sources (`exposure_annual.csv`)

This file holds annual US flight hours by aircraft category. They are the denominators for accident rates. There is one row per (year, category), and hours are raw hours rounded to whole hours. `departures` is filled only for `airliner`.

- **Build:** `uv run python scripts/curate_exposure.py`. It downloads every spreadsheet source into `data/raw/exposure/` (gitignored, checksummed in `data/raw/MANIFEST.json`), extracts each spreadsheet year, merges in the hand-transcribed rows from `exposure_transcribed.csv`, validates the result with `rime.exposure.load_exposure`, and prints its cross-checks.
- **Hand-transcribed years** (PDF or HTML sources only): `airliner` 1992–2002, plus `ga_piston`, `ga_turbine` and `helicopter` for 1999.
- Every row's `source` names the table or sheet and the method. `source_url` is the file itself.

Coverage (sourced years; never interpolated):

| category | first–last | missing inside range | years |
|---|---|---|---|
| airliner | 1992–2024 | none | 33 |
| charter | 2004–2024 | 2011 | 20 |
| ga_piston | 1999–2024 | 2011 | 25 |
| ga_turbine | 1999–2024 | 2011 | 25 |
| helicopter | 1999–2024 | 2011 | 25 |

FAA ran no GA survey for CY2011. That leaves a one-year hole in every survey-based series, and in `charter` too, because its on-demand component comes from the survey. NTSB marks 2011 on-demand hours as "not available".

## Sources

| key | publication | used for |
|---|---|---|
| NTSB-STATS | NTSB *US Civil Aviation Accident Statistics 2005–2024*, `AviationAccidentStatistics_2005-2024_20260112.xlsx` (linked from https://www.ntsb.gov/safety/Pages/research.aspx). Table 5: Part 121 sched+nonsched. Table 8: Part 135 commuter. Table 17: Part 135 on-demand fixed-wing. Table 20: on-demand helicopters (cross-check only) | airliner 2005–2024, charter 2005–2024 |
| NTSB-AR2013 | NTSB Annual Review 2013 workbooks `AnnualReview_2013_Public_2_Part121_20150218.xls` and `..._3_Part135_20150218.xls` (values in millions) | airliner 2004, charter 2004 |
| NTSB-AR2012 | NTSB Annual Review 2012 workbook `AnnualReview_2012_Public_2_Part121_20140113_Final.xlsx` (millions) | airliner 2003 |
| NTSB-HTML5 | NTSB *Aviation Statistical Reports – Table 5*, 1992–2011, HTML table at https://www.ntsb.gov/safety/data/Pages/table5.aspx | airliner 1992–2002 (transcribed) |
| FAA-3.2 | FAA *General Aviation and Part 135 Activity Survey*, chapter III, Table 3.2 "Total Hours Flown by Actual Use by Aircraft Type". One file per survey year (URLs in the script; index at https://www.faa.gov/data_research/aviation_data_statistics/general_aviation) | ga_piston, ga_turbine, helicopter 2000–2024 |
| FAA-1999 | FAA GA survey CY1999 Table 3.2, PDF `cy1999/tab_3-2.pdf` | ga_piston, ga_turbine, helicopter 1999 (transcribed) |
| FAA-CH1 | FAA GA survey CY2024 chapter I, Table 1.3 (total hours by aircraft type, 2013–2024) | cross-check only |
| NTSB-AR2019 | NTSB Annual Review 2019 workbooks (`..._20211215.xlsx`) | discrepancy check only |

## airliner

**Definition:** US air carriers operating under 14 CFR 121, scheduled and nonscheduled service. Flight hours and departures are compiled by FAA, as the NTSB tables note.

| years | source | where |
|---|---|---|
| 2005–2024 | NTSB-STATS | sheet `Table 5`, columns "Flight Hours" and "Departures" |
| 2004 | NTSB-AR2013 | sheets `Part121_FlightHours` and `Part121_Departures` (millions × 10⁶) |
| 2003 | NTSB-AR2012 | sheets `Part121_FlightHours` and `Part121_Departures` (millions × 10⁶) |
| 1992–2002 | NTSB-HTML5 | HTML table rows 1992–2002, columns "Flight Hours" and "Departures" |

- **Derivation:** none. Values are copied as published.
- **First sourced year:** 1992.
- **Gaps:**
  - 1990–1991 could not be sourced. NTSB's online table starts in 1992. BTS (`www.bts.gov`) and the DOT National Transportation Library (`rosap.ntl.bts.gov`) both return HTTP 403 to automated requests, so they weren't used (no workaround attempted). The ARA-11/01, ARA-12/01 and ARA-14/01 PDFs give exposure only as charts.
  - **Definition break in 1997:** from 20 March 1997, scheduled passenger aircraft with 10 or more seats moved from Part 135 to Part 121. Part 121 hours jump (13.7 M in 1996, 15.8 M in 1997) and Part 135 commuter hours collapse. The accident side shows the same break.
- **Discrepancies** (newer publication used): the script prints these automatically.
  - Part 121 hours 2008–2011: NTSB-HTML5 vs NTSB-STATS, e.g. 2008 19,097,962 vs 19,126,766 and 2011 17,756,000 vs 17,962,965.
  - 2013: NTSB-AR2013 17,692,748 vs NTSB-STATS 17,779,641.
  - 2019: NTSB-AR2019 19,788,411 vs NTSB-STATS 19,764,009.
  - The overlap years 2003 and 2004 agree across NTSB-HTML5, AR2012 and AR2013.

**Spot checks:**

| year | value | where read |
|---|---|---|
| 2024 | 19,878,434 h; 9,274,699 departures | NTSB-STATS `Table 5`, row 2024 |
| 2004 | 18,882,503 h | NTSB-AR2013 `Part121_FlightHours`, row 2004 (18.882503). The same value appears in the NTSB-HTML5 row 2004 |
| 1995 | 13,505,257 h; 8,457,465 departures | NTSB-HTML5, row 1995 |

## charter

**Definition:** Part 135 fixed-wing hours = commuter (scheduled) Part 135 hours + on-demand (air taxi, air tour, air medical) fixed-wing hours.

| years | source | where | method |
|---|---|---|---|
| 2005–2024 | NTSB-STATS | `Table 8` "Flight Hours" (commuter) + `Table 17` "Flight Hours" (on-demand, fixed-wing airplanes) | Fixed-wing split as published. NTSB Table 17 equals the FAA survey's fixed-wing Part 135 hours exactly: the script checks Table 17 against FAA-3.2 for every year, and the maximum difference is 0 h |
| 2004 | NTSB-AR2013 | `Part135_Scheduled_FlightHours` + `Part135_NonSched_FlightHours` column "Fixed Wing" (millions × 10⁶) | Same method. 2,455,585 also equals the FAA 2004 Table 3.2 fixed-wing on-demand Air Taxi + Air Tours + Air Med |

- **Derivation:** charter = commuter + on-demand fixed-wing. Example for 2024: 471,377 + 3,237,778.19 = 3,709,155.
- The fallback "total Part 135 minus survey rotorcraft air-taxi hours" was never needed. Every included year has the fixed-wing split.
- **First sourced year:** 2004.
- **Gaps:**
  - 2011: no FAA survey, so NTSB has no on-demand estimate.
  - 1990–2003 is missing. NTSB-AR2012 states "2003 data is unavailable" for non-scheduled Part 135 hours. No accessible NTSB source gives total on-demand hours before 2004: the HTML table series has Tables 5, 6, 8, 10 and 11 only, with no on-demand table.
  - The survey's pre-2004 "Air Taxi" use can't stand in for it. FAA notes that Part 135 categories were first tabulated separately in 2004, and that up to 2003 commuter activity was folded into Air Taxi. (The 1999 table title instead says commuter aircraft are excluded.) Its 2003 fixed-wing Air Taxi + Air Tours is 1.03 M h against 2.76 M h for 2004, which is a methodology break, not a real change.
  - Commuter-only rows were not entered for 1992–2003. They would not match the definition.
- **Discrepancies** (newer publication used):
  - Part 135 commuter hours, NTSB-AR2013 vs NTSB-STATS: 2012 319,997 vs 322,416; 2013 320,684 vs 325,154.
  - Part 135 commuter hours, NTSB-AR2019 vs NTSB-STATS: 2019 416,797 vs 462,956.
  - Commuter 2008: NTSB-HTML Table 8 293,499 vs NTSB-STATS 296,939.

**Spot checks:**

| year | value | where read |
|---|---|---|
| 2024 | 3,709,155 | NTSB-STATS `Table 8` 2024 = 471,377, plus `Table 17` 2024 = 3,237,778.19. The latter equals FAA 2024 Table 3.2, Fixed Wing: Total, "Part 135 Total Active" = 3,237,778.19 |
| 2015 | 2,752,914 | `Table 8` 359,866 + `Table 17` 2,393,048 |
| 2004 | 2,757,803 | NTSB-AR2013: 0.302218 M + 2.455585 M |

## helicopter

**Definition:** FAA survey total rotorcraft hours, all uses, including Part 135 air taxi, air tour and air medical.

| years | source | where |
|---|---|---|
| 2000–2024 | FAA-3.2 | row "Rotorcraft: Total" (2004–05 spelled "Rotocraft: Total"), "Est. Total Hours", in the all-use total column: column 2 for 2000–2015, column 1 for 2016–2024 |
| 1999 | FAA-1999 | PDF page 3, row "Rotocraft: Total", column "Total" |

- **Derivation:** none.
- **Column-label problems in some FAA files** (the script checks these):
  - In 2016–2022, column 1 is headed "General Aviation Use Total Active" but holds the all-use total. It equals FAA-CH1 Table 1.3, and equals GA uses + Part 135 uses.
  - The 2023 header row is misaligned with its 19 data columns. The real layout is: column 1 total, columns 2–13 GA uses, column 14 GA total, columns 15–17 Part 135 taxi/tours/med, column 18 Part 135 total. This was confirmed by the identities total = GA + Part 135 total for every row used, and by matching NTSB Tables 17 and 20.
- All 2013–2024 type totals match FAA-CH1 Table 1.3. The only differences are 2015, which the CY2024 edition rounds to the thousand.
- **First sourced year:** 1999.
- **Gaps:**
  - 2011 (no survey).
  - Before 1999: FAA's online survey index starts at CY1999.
- **Caution:** the 2003→2004 rise (2.13 M → 2.53 M h) coincides with the 2004 survey redesign.

**Spot checks:**

| year | value | where read |
|---|---|---|
| 2024 | 2,889,877 | FAA 2024 Table 3.2, Rotorcraft: Total, "Total Active" = 2,889,877.09. FAA-CH1 Table 1.3 2024 = 2,889.877 thousand |
| 2006 | 3,445,834 | FAA 2006 Table 3.2, sheet `3.2`, Rotorcraft: Total, column "Total" |
| 1999 | 2,744,490 | FAA-1999 PDF page 3, Rotocraft: Total, "Total" |

## ga_piston

**Definition:**

- Fixed-wing piston hours (single + multi-engine, including "Piston: Other" where shown) minus the survey's Part 135 uses.
- Plus Experimental: Total, all uses.
- Plus light-sport from 2005, when the type was added. The light-sport row depends on the year:
  - 2005–08: "Light-sport".
  - 2009–10: "Light-sport: Total", which covers experimental and special LSA and is separate from Experimental: Total.
  - 2012+: "Special Light-sport". In these years experimental LSA sits inside Experimental: Total.

All experimental and light-sport hours are assigned to piston. This is a judgment call: most are piston, and the survey doesn't split them by engine.

Experimental and LSA hours are taken as all-use totals rather than "minus Part 135":

- Those aircraft cannot hold a Part 135 certificate.
- From 2013, FAA suppresses their Part 135 cells for that reason ("Estimates of Part 135 activity are suppressed for aircraft types that cannot operate under a FAR Part 135 certificate").
- Before that, the few Part 135 hours reported for them are respondent misclassification, for example 3.4% of experimental hours in 2014.

Gliders, lighter-than-air and "Other Aircraft" are excluded.

**Part 135 uses subtracted:**

| years | Part 135 uses subtracted |
|---|---|
| 1999–2003 | "Air Taxi" + "Air Tours". The table note says Air Tours are Part 135 tours. The pre-2004 "Medical" column mixes Part 91 and Part 135 and can't be split, so it stays in GA |
| 2004–2022 | the three "On-Demand FAR Part 135" columns: Air Taxi + Air Tours + Air Med |
| 2023–2024 | the published GA-use total column is used directly: column 14 in 2023, "General Aviation Use Total Active" (column 2) in 2024. The script checks it equals total − "Part 135 Total" |

**Suppressed cells** ("*") in the piston Part 135 columns:

- **Recovered exactly** from the fixed-wing row, as piston = FW − turboprop − turbojet (Fixed Wing: Total = piston + turboprop + turbojet holds in every year, checked by the script):
  - 2015 Air Med (8,343)
  - 2017 Air Med (15,575)
  - 2018 Air Med (11,758)
  - 2019 Air Med (2,433)
  - 2020 Air Med (2,172)
  - 2022 Air Med (15,805)
- **Allocated** where two cells in a column are suppressed. The fixed-wing residual is split by the two types' total hours:
  - 2020 Air Tours: piston and turboprop both suppressed. Residual 13,058 h, piston share 11,055.
  - 2022 Air Tours: piston and turbojet both suppressed. Residual 20,544 h, piston share 15,073.

  The maximum possible error is the residual: under 0.1% of `ga_piston` and under 0.5% of `ga_turbine`. The `source` field records each case.

**Worked derivations:**

- 2006: 16,525,445 − (928,848 + 46,154 + 74,667) + 1,217,886 + 65,871 = 16,759,533.
- 1999: 22,894,957 − 882,695 − 16,787 + 1,247,767 = 23,243,242.

**First sourced year:** 1999.

**Gaps:** 2011 (no survey), and before 1999 (no FAA tables online).

**Caution:** the 2004 survey redesign is a level break. From 2004, Part 135 uses are tabulated separately and commuter activity is excluded. The pre-2004 Air Taxi use is much smaller, so 1999–2003 GA hours likely still contain some Part 135 flying. A sensitivity check that excludes, or adds a step at, 2003/2004 is advisable.

**Spot checks:**

| year | value | where read |
|---|---|---|
| 2024 | 17,657,701 | FAA 2024 Table 3.2: Piston: Total "General Aviation Use Total Active" 15,909,765.68 + Experimental: Total "Total Active" 1,309,532.05 + Special Light-sport 438,403.64 |
| 2006 | 16,759,533 | FAA 2006 Table 3.2, sheet `3.2` (worked derivation above) |
| 1999 | 23,243,242 | FAA-1999 PDF: page 1 Piston: Total (Total 22,894,957; Air Taxi 882,695; Air Tours 16,787) and page 4 Experimental: Total 1,247,767 |

## ga_turbine

**Definition:** fixed-wing turboprop + turbojet hours ("Turboprop: Total" + "Turbojet: Total") minus the same Part 135 uses as `ga_piston`. In 2006–2007 there is no "Turbojet: Total" row, and the values sit on the "Fixed Wing - Turbojet" heading row.

- **Derivation:** turbine Part 135 = Fixed Wing: Total Part 135 − piston Part 135. This makes the result exact whenever the piston cell is known or recovered. Suppressed turboprop or turbojet cells don't matter on their own.
- **Allocation years:** in 2020 and 2022, `ga_turbine` takes the complement of the residual split described under `ga_piston`.
- **2023–2024:** turboprop + turbojet GA-use totals, as published.
- **Worked derivation (2006):** turboprop 2,162,305 − (466,654 + 8,409 + 76,231) = 1,611,011, and turbojet 4,077,209 − (880,332 + 17 + 62,938) = 3,133,922. The sum is 4,744,933.
- **First sourced year:** 1999.
- **Gaps:** 2011, and before 1999.
- **Caution:** the 2004 survey redesign is a level break. Turbojet totals jump from 2.70 M h (2003) to 3.72 M h (2004).

**Spot checks:**

| year | value | where read |
|---|---|---|
| 2024 | 5,064,275 | FAA 2024 Table 3.2 "General Aviation Use Total Active": Turboprop 1,950,628.89 + Turbojet 3,113,646.30 |
| 2006 | 4,744,933 | FAA 2006 Table 3.2, sheet `3.2` (worked derivation above) |
| 2000 | 4,061,149 | FAA 2000 Table 3.2, sheet `Table 3.2`: Turboprop 2,031,394 − 407,263 − 5,281, plus Turbojet 2,755,210 − 312,911 − 0 |

## Notes

- Rates built on these hours are national and annual. They are coarse, and the survey estimates carry standard errors of about 1–5% per type (published next to each estimate).
- 2024 survey values are published with decimals and are rounded to whole hours here.
- Sites blocked for automated access, not used, and not worked around:
  - `www.bts.gov` (HTTP 403)
  - `rosap.ntl.bts.gov` (HTTP 403)
  - `corpora.tika.apache.org` (a mirror of old NTSB reviews). This one did not resolve; it isn't a block.
