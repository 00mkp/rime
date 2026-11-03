# Manual tables

Hand-curated inputs, committed to the repo. Each one lists its source here.

- `regions.csv`: maps each US state to its NOAA NCEI U.S. climate region (Karl & Koss, 1984). Alaska and Hawaii are their own regions. Source: https://www.ncei.noaa.gov/access/monitoring/reference-maps/us-climate-regions
- `wx_codes.csv` decides which NTSB codes count as "weather-involved".
  - **2008 onward:** findings whose code starts with `0303` (Environmental issues → Conditions/weather/phenomena), except light condition (`030360`).
  - **Before 2008:** the sequence-of-events subject `20000` "WEATHER CONDITION", where the modifier code names the weather (e.g. 2213 icing conditions, 2224 turbulence, 2228 thunderstorm), plus occurrence codes 240 and 330 (encounter with weather).
  - Wake turbulence is excluded explicitly. Code meanings come from the `ct_seqevt` table and the `eADMSPUB_DataDictionary` in the NTSB database.
