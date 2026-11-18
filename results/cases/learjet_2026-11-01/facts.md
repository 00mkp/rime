# Learjet 60 crash near Greenacres, FL (2026-11-01): preliminary weather reconstruction

**Preliminary; not a cause determination.** NTSB's investigation (ERA27MA026) is ongoing. This page shows what public radar and satellite data recorded near the crash, as an illustration of rime's method. It will be updated when NTSB publishes the flight track in its preliminary report (expected around 2026-12-01).

## What NTSB has said (public statements, 2026-11-02)

- The flight departed Austin, TX about 10:37 a.m. ET for North Eleuthera, Bahamas, cruising at 35,000 ft.

- About 12:47 p.m. ET (17:47 UTC), the crew reported light clear icing, moderate turbulence, an outside air temperature of −47 °C, and then precipitation, and requested a climb to 37,000 ft.

- Less than 30 seconds later they announced a descent and a mayday. About 12:48 they reported an overspeed condition and descent. Impact was about 12:51 p.m. ET (17:51 UTC).

- NTSB sees indications of an in-flight breakup. Most of the left elevator was found 1.3–3.8 miles from the impact site.

## What the weather data show

Radar: Miami WSR-88D (KAMX), 117 km south-southwest of the impact point. The volume scan starting 17:45:48 UTC brackets the icing report and the start of the descent.

| Area (around the approximate impact point) | Max reflectivity (dBZ) | Highest 18-dBZ echo top (km) | Area with echo tops ≥ 10.7 km (FL350) | Max reflectivity at 9.5–11.5 km (dBZ) | Coldest GOES-19 cloud top (°C), 17:46 | Area of cloud tops ≤ −60 °C |
|---|---|---|---|---|---|---|
| within 15km | 58.5 | 12.4 | 70 km² | 42.0 | -69.2 | 712 km² |
| within 30km | 58.5 | 12.8 | 209 km² | 42.0 | -69.6 | 2674 km² |
| within 60km | 61.0 | 13.2 | 974 km² | 42.0 | -73.3 | 9013 km² |
| approach sector 60km | 61.0 | 13.2 | 626 km² | 42.0 | -73.3 | 2503 km² |

For context: the reported outside air temperature (−47 °C) is about 7 °C warmer than the standard atmosphere at 35,000 ft (-54.3 °C). At that temperature, ordinary icing from supercooled liquid droplets is rare. Ice-crystal icing inside deep convection is the mechanism usually associated with icing reports this cold.

Every radar volume from 17:35 to 17:57 UTC and every satellite scan from 17:41 to 17:51 UTC is in `radar_stats.csv` and `goes_stats.csv`.

## Limitations

- **Track unknown.** Until NTSB publishes it, the analysis uses rings around the approximate impact point, plus a 60-km wedge to the west-northwest (bearings 250°–330°, the direction of the route from Austin). The wedge is an assumption.

- **Impact point is approximate:** the intersection named in news reports.

- **Radar geometry:** at 117 km from KAMX, the lowest beam passes about 1.5–2 km above the ground, so low-level rain is undersampled. Upper levels, including the cruise layer, are well sampled. A volume scan takes about 5 minutes.

- **Satellite parallax:** high cloud tops appear displaced several km north (away from the satellite at 75.2° W). That's small compared with the 15–60 km areas used here.

- Echo tops are beam-center heights of the highest ≥18-dBZ return. They're approximate to within roughly a beam width (~1 km at this range).

## Sources

- NTSB investigation page: https://www.ntsb.gov/investigations/Pages/ERA27MA026.aspx

- NTSB statements as reported by WPTV, 2026-11-02

- NEXRAD Level II, KAMX: `unidata-nexrad-level2` public AWS bucket

- GOES-19 ABI L2 CMIPC band 13: `noaa-goes19` public AWS bucket
