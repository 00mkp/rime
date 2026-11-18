# Learjet 60 crash near Greenacres, FL (2026-11-01): preliminary weather reconstruction

**Preliminary; not a cause determination.** NTSB's investigation (ERA27MA026) is ongoing. This page shows what public radar and satellite data recorded near the crash, as an illustration of rime's method. It will be updated when NTSB publishes the flight track in its preliminary report (expected around 2026-12-01).

## What NTSB has said (as reported by WPTV from NTSB's 2026-11-02 news conference)

- The flight departed Austin, TX about 10:37 a.m. ET for North Eleuthera, Bahamas, cruising at 35,000 ft.
- About 12:47 p.m. ET (17:47 UTC), the crew reported light clear icing, moderate turbulence, an outside air temperature of −47 °C (−53 °F), and then precipitation, and requested a climb to 37,000 ft. NTSB has not characterized the icing further.
- Less than 30 seconds later they announced a descent and a mayday. About 12:48 they reported an overspeed condition and descent. Impact was about 12:51 p.m. ET (17:51 UTC).
- Investigators have "some indication that the aircraft was breaking before impact", which NTSB describes as preliminary. Most of the left elevator was found in pieces 1.3–3.8 miles (2.1–6.1 km) from the impact site.

## What the weather data show

Radar: Miami WSR-88D (KAMX), 117 km south-southwest of the impact point. The volume scan starting 17:45:48 UTC is the closest to the 17:47–17:48 UTC events. Within it, the tilts that sample about 8–14 km above the impact area (4.0° (beam centre ≈ 8.9 km), 5.1° (beam centre ≈ 11.2 km), 6.4° (beam centre ≈ 13.8 km)) were taken between 17:49:09 and 17:49:49 UTC, roughly 1–2 minutes after the icing report and before impact.

| Area (grid cells whose centres lie within…) | Max reflectivity (dBZ) | Highest 18-dBZ echo top (km MSL) | Area with echo tops ≥ 10.7 km | Max reflectivity at 9.5–11.5 km (dBZ) | Coldest band-13 brightness temperature (°C), scan 17:46 | Area ≤ −60 °C |
|---|---|---|---|---|---|---|
| within 15 km | 58.5 | 12.4 | 70 km² | 42.0 | −69.2 | 712 km² |
| within 30 km | 58.5 | 12.8 | 209 km² | 42.0 | −69.6 | 2674 km² |
| within 60 km | 61.0 | 13.2 | 974 km² | 42.0 | −73.3 | 9013 km² |
| assumed approach sector (60 km) | 61.0 | 13.2 | 626 km² | 42.0 | −73.3 | 2503 km² |

Satellite: GOES-19 ABI band 13 (10.3 µm). For thick cloud, the brightness temperature approximates the cloud-top temperature. The CONUS scan starting 17:46:17 UTC covered this area by 17:48:56.

For context, the reported outside air temperature (−47 °C) is about 7 °C warmer than the standard atmosphere at 35,000 ft (−54.3 °C). 35,000 ft is a pressure altitude, about 10.7 km in the standard atmosphere and roughly 0.2–0.3 km higher in geometric height on a day this warm. The radar heights above are geometric.

Every radar volume from 17:35 to 17:57 UTC and every satellite scan from 17:41 to 17:51 UTC is in `radar_stats.csv` and `goes_stats.csv`. Sweep times for the key volume are in `radar_sweep_times_174548.csv`.

## Limitations

- **Track unknown.** Until NTSB publishes it, the analysis uses rings around the approximate impact point, plus a 60-km wedge to the west-northwest (bearings 250°–330°, the direction of the route from Austin). The wedge is an assumption.
- **Impact point is approximate:** the intersection named in news reports. Areas are built from ~3-km grid cells, so a value can come from a cell just inside a ring's edge.
- **Radar geometry:** at 117 km from KAMX, the beam is ~2 km deep, and the lowest beam passes about 1.5–2 km above the ground, so low-level rain is undersampled. Upper levels are sampled by only a few tilts whose beam centres are 2–3 km apart. Echo tops are therefore quantized by tilt and uncertain to within about 1–3 km. The cruise layer is sampled by two tilts with ~2 km vertical resolution.
- **Satellite parallax:** high cloud tops appear displaced about 7–9 km toward the north-northwest (away from the satellite). That's small compared with the 15–60 km areas used here.

## Sources

- NTSB investigation page: https://www.ntsb.gov/investigations/Pages/ERA27MA026.aspx
- NTSB statements as reported by WPTV, 2026-11-02: https://www.wptv.com/news/palm-beach-county/region-c-palm-beach-county/ntsb-news-conference-learjet-60-crash-in-palm-beach-county/11-2-26
- NEXRAD Level II, KAMX: `unidata-nexrad-level2` public AWS bucket
- GOES-19 ABI L2 CMIPC band 13: `noaa-goes19` public AWS bucket
