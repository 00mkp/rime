# rime: design spec

**Status:** draft for review. Designed in conversation on 2026-11-02.
**Working name:** rime (rime ice: the kind that builds up on airframes). Claude picked it; easy to change.

## 1. Purpose

rime is a public data science study that asks one question:

> Have changing weather patterns, both from long-term climate change and from cycles like El Niño / super El Niño, had a measurable, statistically significant effect on aviation safety incidents in the US?

It also asks a follow-up: when serious crashes happen, what weather was actually there, and are there recurring weather signatures that crash more often than chance would predict?

### Why now / why this

The trigger was the **1 Nov 2026 Learjet 60 crash in Greenacres, Palm Beach County, FL** (Austin → Bahamas, 9 dead). Early reporting says the crew reported ice accumulating at about FL340 with an outside air temperature of -47°C, moderate turbulence, and precipitation. They asked to climb, and they had just passed through a strong storm cell. The cause is not established.

The user believes the chain from climate shift to weather change to aviation incidents is under-analyzed. Prior art exists for **clear-air turbulence** (Paul Williams et al., University of Reading) and **heat-limited takeoff performance**. **Icing**, especially **high-altitude ice crystal icing** in deep convection (the mechanism behind AF447's pitot icing), and the **ENSO angle** have had much less attention. That gap is where rime aims.

### What the user said

- The end product is a **report** answering whether a statistically significant relationship exists.
- Include **all aircraft types**: airliners, business jets, and general aviation.
- **Part 2** should not lean on investigators' crash reports. Build **two independent catalogs**: "there was a crash and this is what happened" and, separately, "there was this weather phenomenon on this day, here". Then cross-reference them.
- The report will be **published publicly** or put in the user's portfolio.
- **Claude builds everything**; the user steers.
- **No deadline.** Build the full scope in order; don't cut scope to publish while the Learjet crash is in the news.
- The user has no preference on repo visibility. **Claude's call:** a public GitHub repo from day one, so the `prereg-v1` tag has a verifiable public timestamp.
- **No OpenSky research application** (see §4c).

### Claude's calls (accepted in conversation, flagged here so they're visible)

- Python, managed with uv; pandas / xarray / statsmodels (others as needed).
- **US only.** NTSB, NEXRAD, FAA activity data, and ADS-B coverage are free and deep for the US and not comparable elsewhere.
- **About 1990 to now.** Individual data sources set their own floors (see §6).
- Each aircraft category is analyzed **separately**, never pooled into one headline number. **Categories:** airliners (Part 121); commuter/charter (Part 135); general aviation (Part 91) split into turbine/business jets vs. piston; helicopters. Business jets appear under both 91 and 135, so they're tagged by aircraft type as well as by Part. **Out of scope:** drones, balloons, gliders, ultralights (no usable exposure data). **In scope:** Alaska and Hawaii, as their own regions, because Alaska's weather and GA accident profile would distort the other 48 states' figures.
- Part 1 is built first, then Part 2.
- NTSB probable-cause findings stay **out of Part 2's matching**. They're used only at the end as a check.

## 2. Goals, non-goals, anti-goals

**Goals**
- A defensible yes, no, or "can't tell, and here's why" on the Part 1 question, per aircraft category, with effect sizes and uncertainty.
- A weather-phenomenon catalog and crash catalog that are each useful on their own, and a cross-reference that says which phenomena raise crash risk relative to their baseline.
- A plain-language public report that a non-specialist can read in about 10 minutes, with methods and limitations for specialists.
- Full reproducibility: one command rebuilds everything from raw data.

**Non-goals**
- Determining the cause of any single crash, including the Learjet. rime is not an investigation.
- Operational tools such as forecasting, flight planning, or alerting.
- Non-US data in v1.
- Attributing weather changes to climate change from first principles. Accepted climate science is cited for that. rime tests the link between weather and incidents.

**Anti-goals (this would be a failure even if the code works)**
- **A spurious "climate is causing crashes" headline.** Raw incident counts over time mostly reflect falling accident rates and rising traffic. Any trend claim must come from rates with exposure, and the trends have to be controlled for.
- **Weather at crash sites described without a baseline.** "Storms were present" means nothing unless we know how often storms are present when nothing happens.
- **Fishing.** Testing dozens of phenomenon × category × region combinations and reporting whichever comes out significant. Primary hypotheses get fixed before results are seen, and everything else is labeled exploratory with multiple-comparison correction.
- **Overclaiming from coarse data.** If a phenomenon is smaller than the data's resolution, the report says so and doesn't infer it.
- **Hiding a null.** If the answer is "no detectable relationship", that's the headline, along with what effect size the study could have detected.

## 3. Part 1: the statistical study

### Question, made testable

Do weather-related aviation accident and incident **rates** (per unit of flight exposure) differ by ENSO phase, and do they show a trend over time that tracks measurable changes in hazardous weather, after controlling for the overall safety trend and traffic?

### Primary hypotheses (fix before looking at outcomes)

- **H1 (ENSO):** Weather-related accident rates differ between El Niño, La Niña, and neutral periods, by region and season, in the directions ENSO's known US effects predict. Examples: a stronger, more southerly winter jet stream and a wetter southern tier during El Niño; altered Atlantic hurricane activity.
- **H2 (hazard trend):** The frequency of specific hazardous-weather conditions (deep convection reaching cruise altitudes, icing-favorable layers, strong vertical wind shear near the jet) has changed over the period, and accident rates for the matching weather categories move with them.
- **H3 (ice crystal icing):** High-altitude icing and convection-related events at cruise have become more common relative to exposure. This one is motivated by the Learjet case and may be underpowered; the report must say so if it is.

### Outcome data

- **NTSB accident and incident database** (CAROL / downloadable database). For Part 1 only, NTSB's weather-related coding is used to classify events as weather-involved. The coding scheme changed around 2008 (occurrence and findings codes), so the classification must be harmonized across that break and checked for a discontinuity.
- **NASA ASRS** voluntary reports, as a secondary signal for non-accident weather encounters. Reporting is voluntary, so it's a biased sample; use it for corroboration, not primary inference.

### Exposure (denominators)

- Airliners (Part 121): BTS T-100 / on-time data, departures and hours.
- Part 135 and general aviation (Part 91): FAA General Aviation and Part 135 Activity Survey (annual hours by category). It's coarse (annual, national or regional), and the report must say so.
- FAA OPSNET/ATADS airport operations where finer resolution is needed.

### Weather and climate covariates

- **ONI** (NOAA CPC) for ENSO phase and strength; "super" El Niño = ONI ≥ 2.0 (1997–98, 2015–16, and 2023–24 if it qualifies).
- **ERA5** reanalysis for hazard-condition frequencies (H2/H3) over time.

### Method (direction; details left to the builder)

- Count regression, Poisson or negative binomial, of weather-related events by month × region × category, with an exposure offset, seasonality, a long-run safety-trend term, and ENSO phase/ONI as the covariate of interest.
- **Pre-registration (Claude's call):** after the data is downloaded, the only outcome data looked at is total event counts per category and year, for the power analysis. Claude then drafts concrete H1–H3 specs: regions, seasons, outcomes, lags, models, and thresholds. The user approves them, and they're committed and git-tagged (`prereg-v1`) before any weather-coded split by ENSO or hazard is computed. Anything outside the tag is labeled exploratory in the report.
- A **power analysis** up front: given the event counts per category, what's the smallest effect detectable? Airliner weather accidents are so rare that the answer may be "not testable", and saying that is a valid result.
- Sensitivity checks: different ENSO lags, excluding the 2008 coding break, all accidents vs. weather-coded only, regional definitions.

## 4. Part 2: the two catalogs and the cross-reference

### 4a. Crash catalog: "there was a crash and this is what happened"

The physical facts of each event, deliberately not the investigators' conclusions:
- time (UTC), lat/lon, altitude, phase of flight, aircraft type and category, operation type
- what the aircraft did: e.g., sudden altitude loss, loss of control in flight, controlled flight into terrain, ground impact
- injury severity
- the flight track where available (OpenSky ADS-B archive, about 2016 onward)

The source is NTSB factual data. **Where the line is (Claude's call):** physical facts are allowed even when they come from investigators: structured fields, NTSB occurrence codes describing what the aircraft did (e.g., "loss of control in flight"), and time and altitude extracted from the factual narrative when structured fields lack them. Excluded from matching: probable cause, contributing factors, findings, and any weather the investigators attributed to the event. Narrative extraction is limited to physical facts and records where each value came from.

**Scope:** fatal and serious accidents across all categories over the study period, plus major incidents.

### 4b. Weather phenomenon catalog: "there was this weather on this day, here"

Built from raw weather data with **no reference to crashes**. Each record has a phenomenon type, time span, footprint, altitude range, and intensity.

**Coverage tiers (Claude's call, to stay at laptop scale):**
- **Tier 1, complete:** the whole US, every day of the study period, from compact sources: ERA5 at a reduced set of pressure levels and variables, gridded radar mosaics (e.g., GridRad / MRMS echo tops where archived) or NEXRAD Level III summaries, SIGMETs/AIRMETs/PIREPs, and Storm Events. This tier is what makes the catalog useful on its own and what feeds the ENSO and decade frequencies.
- **Tier 2, high-resolution windows:** full NEXRAD Level II and GOES imagery only around crashes and their case-crossover control windows.
- If a phenomenon type can't be built for Tier 1 at laptop scale, it's documented as window-only, and it drops out of the frequency and trend analysis.

| Phenomenon | Primary source | Notes |
|---|---|---|
| Convective storm cells (incl. tops reaching cruise altitude) | NEXRAD Level II (AWS open data; network complete about 1997) | Echo tops, VIL; this is the resolution the Learjet case needs |
| Deep convection / cold cloud tops | GOES-16+ (2017+), earlier GOES at coarser resolution | Overshooting tops; proxy for high ice-water content |
| Icing-favorable layers | ERA5 (temperature, humidity, cloud liquid/ice water by level) | about 30 km / hourly: synoptic-scale only |
| Jet stream shear / clear-air turbulence potential | ERA5 (Ellrod-type indices, wind shear) | |
| Deep low-pressure systems, fronts | ERA5 | |
| Officially warned hazards | IEM archives of SIGMETs/AIRMETs and PIREPs; NOAA Storm Events | Archive start dates need checking |

### 4c. Cross-reference

- **Matching:** a crash "intersects" a phenomenon if it falls inside its footprint and altitude range within a time window. The builder sets the tolerances and reports them.
- **Baseline / controls:**
  - **Case-crossover design** for the full period: compare the weather at each crash's location and time with the same location and time of day on control days (same month, other years or nearby days). This is standard in environmental epidemiology, and it controls for place and season.
  - **Traffic exposure**, about 2017 onward: estimate how many flights cross each phenomenon, giving a crash rate per crossing. **No OpenSky research application** (user's preference; Claude agreed it isn't needed). Use the free public **OpenSky state-vector samples** (`s3.opensky-network.org/data-samples/states/`, verified 2026-11-02): full-day, hourly-file snapshots for every Monday from 2017-06-05 to 2022-06-27, about 260 days, global. Build a traffic-density climatology from them (location × altitude band × hour × month × aircraft class), and apply it to phenomena across the period. The license is for non-profit research and education, so attribute OpenSky and keep the study non-commercial. Known limitation: incomplete coverage of low-altitude GA in rural areas, stated in the report. Flight tracks for specific crashes come from the NTSB docket (radar/ADS-B data) where available. Reconsider the research application only if Part 2 conclusions turn out to hinge on exact traffic.
- **Output:** relative risk by phenomenon type and intensity, by aircraft category and phase of flight. Then the same phenomenon frequencies broken out by ENSO phase and by decade, which ties back to Part 1.
- **Final check:** compare rime's matches against NTSB probable-cause and meteorology factual reports for a sample of well-documented accidents. Agreement validates the method; disagreement is reported and interesting.

### 4d. The Learjet as a live case

Reconstruct the 1 Nov 2026 Greenacres crash's weather from NEXRAD, GOES, and ERA5 once the NTSB preliminary report gives the track and timeline. Present it as an illustration of the method, explicitly **not** a cause determination. It must not delay the main study.

## 5. The report

- A public **web page**: plain-language findings first, charts, then methods, limitations, and data sources. Hosting (GitHub Pages or similar) is decided when publishing.
- Structure: the question → the short answer → Part 1 findings → Part 2 findings → the Learjet illustration → what this does and doesn't show → methods → reproducibility.
- Tone: careful. People died in these events; no sensationalism, and no implied blame for crews.

## 6. Constraints

- **Free, public data only.** ERA5 needs a free Copernicus CDS account; the user creates it when needed.
- **Laptop scale.** ERA5 and NEXRAD are enormous. Pull only what's needed: subset in space, time, and level around events and controls, plus regional climatologies for H2. Cache raw downloads and document disk usage.
- **Reproducible.** Scripted pipeline from raw download to report, with pinned dependencies and recorded data versions and download dates.
- **Open source**, in line with the user's other projects. No personal setup details in the repo.
- Source floors: NTSB consistent from about 1982; NEXRAD full network about 1997; GOES-16 2017; OpenSky about 2016; ERA5 and ONI well before 1990.

## 7. Left to the builder

- Exact statistical model specs, lags, and tolerances (within §3–4 and the anti-goals)
- Phenomenon-detection algorithms and thresholds
- Repo layout, pipeline tooling, caching, tests for data-processing code
- Chart design and the report's site generator
- Order of work within each part, and when to cut a phenomenon type that proves infeasible (and documenting why)
