# Manual tables

Hand-curated inputs, committed to the repo. Each one lists its source here.

- `regions.csv`: maps each US state to its NOAA NCEI U.S. climate region (Karl & Koss, 1984). Alaska and Hawaii are their own regions. Source: https://www.ncei.noaa.gov/access/monitoring/reference-maps/us-climate-regions
- `wx_codes.csv` decides which NTSB codes count as "weather-involved".
  - **2008 onward:** findings whose code starts with `0303` (Environmental issues → Conditions/weather/phenomena), except light condition (`030360`) and wake turbulence (`03032025`), **or** a weather occurrence in `Events_Sequence`. The last 3 digits of that code name the occurrence: 210 structural icing, 360/362 turbulence, 390 windshear or thunderstorm, 400 other weather, 401 VFR into IMC. Wake (361) is excluded.
  - **Before 2008:** the sequence-of-events subject `20000` "WEATHER CONDITION" with a weather modifier in 2200–2299 (e.g. 2213 icing conditions, 2224 turbulence, 2228 thunderstorm), **or** occurrence codes 240/330 (encounter with weather). Wake turbulence (24715, 410) is excluded.
  - Code meanings come from the `ct_seqevt` table and the `eADMSPUB_DataDictionary` in the NTSB database.
- `oni_snapshot.txt`: NOAA CPC ONI as retrieved on 2026-11-02. The analysis reads this pinned copy, because CPC revises recent values. Source: https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
- `data_versions.json`: sha256 and retrieval date of every downloaded input, pinned for the pre-registration.
