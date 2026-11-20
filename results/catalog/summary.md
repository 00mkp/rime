# rime crash catalog: coverage and quality

16,431 aircraft involvements in fatal or serious US accidents, 1990–2024 (aircraft categories per the spec). Physical facts only: no weather fields, findings, or cause text.

## Coverage by decade

| decade | rows | time_ok | daynight_mismatch | has_latlon | has_altitude | phase_known |
|---|---|---|---|---|---|---|
| no time | 51 | 0.0% | 0.0% | 92.2% | 15.7% | 76.5% |
| 1990s | 6351 | 99.1% | 0.9% | 85.3% | 17.8% | 98.1% |
| 2000s | 4864 | 99.0% | 1.0% | 96.9% | 24.4% | 98.8% |
| 2010s | 3649 | 99.3% | 0.7% | 100.0% | 26.7% | 99.2% |
| 2020s | 1516 | 98.9% | 1.1% | 100.0% | 28.4% | 98.5% |

`time_ok` means NTSB's stored UTC time is consistent with day/night: the sun's elevation at that place and time agrees with NTSB's light condition. A mismatch suggests the stored time is wrong, so those rows shouldn't be matched to weather by time.

## Phase of flight (harmonized)

| phase | rows |
|---|---|
| maneuvering | 3845 |
| takeoff | 3551 |
| cruise | 3365 |
| approach | 2759 |
| landing | 887 |
| climb | 700 |
| descent | 661 |
| unknown | 244 |
| standing | 242 |
| taxi | 116 |
| other | 61 |

## Altitude spot check (10 random extractions)

Altitude comes from the factual narrative and is used only when a pattern explicitly ties a number to flight altitude. It is an altitude the narrative ties to the flight, not necessarily the altitude at the moment of the accident. In spot checks about 8–9 of 10 extractions were the flight's actual altitude in the accident sequence. Each row keeps the source text (`altitude_span`) so it can be checked.

- `WPR12FA282` → **2,000 ft agl**: …s that pilots should make every effort to fly not less than 2,000 feet above ground level.  The pilot's postaccident ethanol levels were indicative…
- `CEN21FA198` → **20,200 ft msl**: …a gradual reduction in groundspeed began. After reaching an altitude of about 20,200 ft msl, the airplane began a descent on a southeast heading. Just …
- `BFO96FA007` → **500 ft agl**: …hey would fly by a cottage at reduced airspeed and at about 500 feet agl, then they would climb to a higher altitude for more photog…
- `DCA05MA083` → **37,000 ft fl**: …The captain stated that after takeoff he waited until FL370, and well past the line of weather, to turn off the seat be…
- `ERA14FA112` → **145 ft agl**: … then turned left towards the threshold and descended to an altitude of about 145 ft above ground level over the runway threshold before the pilot performed a miss…
- `ERA12LA401` → **2,300 ft msl**: …controllers appropriately instructed them to maintain their altitude (which was 2,300 ft mean sea level [msl]) for separation until they had the traffic in sight; …
- `FTW00FA201` → **100 ft agl**: …Witnesses observed the airplane approximately 80 to 100 feet agl in a 'very steep' nose high angle during the takeoff climb.…
- `WPR14FA132` → **9,000 ft msl**: …cally crossed the mountain range at an altitude of 8,500 to 9,000 ft msl, which provided limited terrain clearance.  After success…
- `ERA09LA131` → **300 ft agl**: …ine made a "couple of popping sounds and went silent" about 300 feet above ground level. The airplane was then observed in a left bank and 45-degre…
- `ERA13FA115` → **3,300 ft unspecified**: … (2531). Shortly thereafter, the airplane reached a maximum altitude of about 3,300 ft and then entered a descending right turn. The airplane's en…
