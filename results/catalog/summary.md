# rime crash catalog: coverage and quality

16,431 aircraft involvements in fatal or serious US accidents, 1990–2024, in the spec's aircraft categories. Physical facts only: no weather fields, findings, or cause text. Where the defining (post-2008) or first (pre-2008) event is an investigator-attributed weather encounter (1,561 rows, e.g. 'VFR encounter with IMC'), the event text is withheld. The phase is kept.

## Coverage by decade

| decade | rows | time_ok | time_unchecked | daynight_mismatch | has_latlon | has_altitude | phase_known |
|---|---|---|---|---|---|---|---|
| no time | 51 | 0.0% | 0.0% | 0.0% | 92.2% | 15.7% | 76.5% |
| 1990s | 6351 | 80.3% | 18.7% | 0.9% | 85.3% | 16.5% | 98.1% |
| 2000s | 4864 | 91.2% | 7.8% | 1.0% | 96.9% | 22.9% | 98.8% |
| 2010s | 3649 | 95.8% | 3.5% | 0.7% | 100.0% | 25.6% | 99.2% |
| 2020s | 1516 | 95.8% | 3.1% | 1.1% | 100.0% | 27.3% | 98.5% |

## Coverage by aircraft category

| category | rows | time_ok | time_unchecked | daynight_mismatch | has_latlon | has_altitude | phase_known |
|---|---|---|---|---|---|---|---|
| airliner | 536 | 72.4% | 23.1% | 2.8% | 85.8% | 32.6% | 100.0% |
| charter | 534 | 81.8% | 12.5% | 5.4% | 92.5% | 25.1% | 98.7% |
| ga_piston | 12978 | 88.8% | 10.2% | 0.7% | 93.6% | 20.8% | 98.4% |
| ga_turbine | 924 | 87.7% | 11.4% | 0.6% | 93.0% | 28.0% | 99.0% |
| helicopter | 1459 | 91.0% | 8.4% | 0.5% | 94.7% | 17.5% | 98.7% |

## How good are the times?

NTSB stores event times in UTC. `ok` means the time was checked and is consistent with NTSB's day/night code: the sun's elevation at that place and time agrees with day or night. `unchecked` means no check was possible (no coordinates, or twilight/unknown light condition). `daynight_mismatch` means the stored time is likely wrong.

The mismatch rate is only a **lower bound** on time errors. Shifting every time artificially shows that the check catches about 2–4% of 1-hour errors, 8–10% of 2-hour errors, and 15–17% of 3-hour errors. It can't see **24-hour date errors** at all, and those exist: an evening local time stored with the local date instead of the next UTC date (e.g. Pinnacle 3701, DCA01MA017). Spot checks against narrative local times suggest a few percent of rows are off by an hour or more. Any weather matching must use time windows of several hours and a date-shift sensitivity check.

## Phase by source database (harmonized phase, share of rows)

Post-2008 uses the phase of NTSB's *defining event*; pre-2008 uses the phase of the aircraft's *first occurrence*. The two are close but not identical, so compare across 2008 with care.

| phase | avall | pre2008 |
|---|---|---|
| approach | 17.3% | 16.5% |
| climb | 2.6% | 5.2% |
| cruise | 19.0% | 21.4% |
| descent | 4.3% | 3.9% |
| landing | 6.1% | 5.0% |
| maneuvering | 22.7% | 23.8% |
| other | 0.5% | 0.3% |
| standing | 1.3% | 1.6% |
| takeoff | 24.7% | 19.8% |
| taxi | 0.5% | 0.8% |
| unknown | 1.1% | 1.7% |

## Altitude spot check (10 random extractions)

Altitude comes from the factual narrative and is used only when a pattern explicitly ties a number to flight altitude, excluding density altitude, airport/field elevation, forecasts, and guidance. It is an altitude the narrative ties to the flight, not necessarily the altitude at the moment of the accident. On 2026-11-19 a reviewer checked 22 spans and found 19 correct (about 86%); the three errors (two density altitudes, one airport elevation) are now excluded. Each row keeps its source text (`altitude_span`) so it can be checked.

- `ERA14LA369` → **2,500 ft agl**: …flight. The departure was uneventful, and the airplane was cruising about 2,500 ft above ground level and was about 2 hours into the planned 3 hour 30 minute fl…
- `NYC06FA205` → **400 ft agl**: …tor initiated an unplanned simulated engine failure during takeoff, about 400 feet agl.  The private pilot flew the L/D max speed as he initiated a 30-degree ri…
- `ANC03FA051` → **9,000 ft msl**: … the anticipated flight route.  The summit of the pass is situated about 9,000 feet msl, and oriented about east/west.  The flight's anticipated direction of tr…
- `ERA24FA026` → **6,000 ft msl**: …ed that about 20 minutes after departing, and while flying at an altitude of about 6,000 ft msl, the airplane’s speed began increasing, reaching a maximum of ab…
- `WPR11LA137` → **137 ft agl**: …ed data point prior to the power lines showed the airplane at an altitude of about 137 feet agl. Representatives from the electrical company reported that the a…
- `ERA09FA145` → **9,700 ft unspecified**: …irst recorded the airplane about 1244 central standard time at an altitude of about 9,700 feet about 50 nm southwest of HTS and then showed the airplane turning…
- `DCA92MA049` → **2,100 ft msl**: …DENTIFIED ON RADAR. THE TWO AIRPLANES COLLIDED APRX 2 MI FROM THE ARPT AT 2,100 FT MSL. THE COLLISION TOOK PLACE JUST OUTSIDE AND TO THE EAST OF THE INDIANAPOLI…
- `LAX06LA141` → **4,600 ft agl**: …at the airplane was in cruise flight heading southwest between 4,300 and 4,600 feet agl.  The last radar return was recorded approximately 0.58 nautical miles (…
- `LAX91FA190` → **13,000 ft unspecified**: …MSL. 40 MI WEST LAY THE CENTRAL VALLEY OF CA, ELE 300 FT MSL.  WHILE CRUISING AT 13,000 FT THE PLT REVERSED COURSE & DISAPPEARED FM RADAR.  THE ACFT CRASHED IN…
- `FTW95LA309` → **10,500 ft msl**: …DURING AN ATTEMPTED FREESTYLE JUMP FROM 10,500 FEET MSL, THE PARACHUTIST GRIPPED A BAR IN THE AIRPLANE, THEN SWUNG HIS LEGS OUT…
