# rime H1 results: ENSO and weather-involved accident rates

Pre-registration: tag `prereg-v1` (`18299e7dc71d`). Run: 2026-11-03T01:48:56+00:00.

## Short answer

**H1-N:** 0 of 9 tests significant after Holm correction.

- Airliner, El Niño: no detectable relationship; the data rule out effects outside −36% to +27%.
- Airliner, La Niña: no detectable relationship; the data rule out effects outside −46% to +20%.
- Charter, El Niño: no detectable relationship; the data rule out effects outside −42% to +38%.
- Private turbine-plane, El Niño: no detectable relationship; the data rule out effects outside −24% to +56%.
- Private turbine-plane, La Niña: no detectable relationship; the data rule out effects outside −17% to +82%.
- Private piston-plane, El Niño: no detectable relationship; the data rule out effects outside −8% to +11%.
- Private piston-plane, La Niña: no detectable relationship; the data rule out effects outside −8% to +13%.
- Helicopter, El Niño: no detectable relationship; the data rule out effects outside −18% to +52%.
- Helicopter, La Niña: nominally 50% more (95% CI 9–107%) weather-involved accidents (unadjusted p = 0.014), but not significant after correcting for multiple tests (Holm p = 0.12). Exploratory evidence only.

**H1-R:** 0 of 2 tests significant after Holm correction.

- The southern tier's share of weather-involved private piston-plane accidents in El Niño winters: no detectable relationship; the data rule out odds changes outside −10% to +55%.
- The northern tier's share of weather-involved private piston-plane accidents in La Niña winters: opposite to the predicted direction, odds 29% lower (95% CI 6–47%). The one-sided confirmatory test can't be significant in this direction; treat it as exploratory.

## Every confirmatory test

| family | test | rr | ci_lo | ci_hi | p | p_holm | reject | n_events | status | model |
|---|---|---|---|---|---|---|---|---|---|---|
| H1-N | airliner el_nino | 0.904 | 0.641 | 1.27 | 0.563 | 1 | False | 308 | ok | nb |
| H1-N | airliner la_nina | 0.806 | 0.542 | 1.2 | 0.286 | 1 | False | 308 | ok | nb |
| H1-N | charter el_nino | 0.898 | 0.584 | 1.38 | 0.624 | 1 | False | 195 | ok | nb |
| H1-N (exploratory) | charter la_nina | 0.933 | 0.578 | 1.5 | 0.775 |  |  | 195 | ok | nb |
| H1-N | ga_turbine el_nino | 1.09 | 0.757 | 1.56 | 0.656 | 1 | False | 295 | ok | nb |
| H1-N | ga_turbine la_nina | 1.23 | 0.828 | 1.82 | 0.308 | 1 | False | 295 | ok | nb |
| H1-N | ga_piston el_nino | 1.01 | 0.918 | 1.11 | 0.836 | 1 | False | 4628 | ok | nb |
| H1-N | ga_piston la_nina | 1.02 | 0.916 | 1.13 | 0.759 | 1 | False | 4628 | ok | nb |
| H1-N | helicopter el_nino | 1.12 | 0.825 | 1.52 | 0.467 | 1 | False | 428 | ok | nb |
| H1-N | helicopter la_nina | 1.5 | 1.09 | 2.07 | 0.0138 | 0.124 | False | 428 | ok | nb |
| H1-R | H1-Ra ga_piston southern tier share, el_nino winters | 1.18 | 0.896 | 1.55 | 0.121 | 0.242 | False | 1378 | ok | nb |
| H1-R | H1-Rb ga_piston northern tier share, la_nina winters | 0.706 | 0.529 | 0.942 | 0.991 | 0.991 | False | 1378 | ok | nb |

## Negative control (non-weather accidents, same models)

| test | rr | ci_lo | ci_hi | p | p_holm | reject | n_events | status |
|---|---|---|---|---|---|---|---|---|
| airliner el_nino | 1.13 | 0.864 | 1.48 | 0.375 | 1 | False | 555 | ok |
| airliner la_nina | 1.18 | 0.877 | 1.59 | 0.275 | 1 | False | 555 | ok |
| charter el_nino | 1.14 | 0.841 | 1.54 | 0.401 | 1 | False | 476 | ok |
| charter la_nina | 1.06 | 0.784 | 1.43 | 0.707 |  |  | 476 | ok |
| ga_turbine el_nino | 1.06 | 0.881 | 1.27 | 0.539 | 1 | False | 1255 | ok |
| ga_turbine la_nina | 0.97 | 0.798 | 1.18 | 0.757 | 1 | False | 1255 | ok |
| ga_piston el_nino | 1.02 | 0.965 | 1.07 | 0.556 | 1 | False | 16445 | ok |
| ga_piston la_nina | 1.08 | 1.02 | 1.14 | 0.00616 | 0.0554 | False | 16445 | ok |
| helicopter el_nino | 1.07 | 0.93 | 1.23 | 0.348 | 1 | False | 2148 | ok |
| helicopter la_nina | 1.08 | 0.929 | 1.25 | 0.322 | 1 | False | 2148 | ok |

No negative-control test was significant: ENSO phase doesn't shift non-weather accidents, as expected.

## Sensitivity analyses (pre-specified, not confirmatory)

| sensitivity | category | phase | rr | ci_lo | ci_hi | p | n_events | status | model |
|---|---|---|---|---|---|---|---|---|---|
| lag3 | airliner | el_nino | 0.892 | 0.631 | 1.26 | 0.519 | 308 | ok | nb |
| lag3 | airliner | la_nina | 0.757 | 0.501 | 1.14 | 0.187 | 308 | ok | nb |
| lag3 | charter | el_nino | 0.924 | 0.589 | 1.45 | 0.731 | 195 | ok | nb |
| lag3 | charter | la_nina | 1.11 | 0.67 | 1.83 | 0.694 | 195 | ok | nb |
| lag3 | ga_turbine | el_nino | 1.17 | 0.806 | 1.7 | 0.41 | 295 | ok | nb |
| lag3 | ga_turbine | la_nina | 1.14 | 0.746 | 1.73 | 0.55 | 295 | ok | nb |
| lag3 | ga_piston | el_nino | 1.01 | 0.91 | 1.12 | 0.874 | 4628 | ok | nb |
| lag3 | ga_piston | la_nina | 0.947 | 0.85 | 1.06 | 0.323 | 4628 | ok | nb |
| lag3 | helicopter | el_nino | 0.757 | 0.541 | 1.06 | 0.103 | 428 | ok | poisson_boundary |
| lag3 | helicopter | la_nina | 0.888 | 0.636 | 1.24 | 0.488 | 428 | ok | poisson_boundary |
| fatal_wx | airliner | el_nino |  |  |  | 1 | 6 | not_estimable | nb |
| fatal_wx | airliner | la_nina |  |  |  | 1 | 6 | not_estimable | nb |
| fatal_wx | charter | el_nino | 1.89 | 0.821 | 4.33 | 0.135 | 53 | ok | poisson_boundary |
| fatal_wx | charter | la_nina | 1.3 | 0.515 | 3.29 | 0.578 | 53 | ok | poisson_boundary |
| fatal_wx | ga_turbine | el_nino | 1.09 | 0.592 | 1.99 | 0.79 | 105 | ok | nb |
| fatal_wx | ga_turbine | la_nina | 1.62 | 0.831 | 3.14 | 0.157 | 105 | ok | nb |
| fatal_wx | ga_piston | el_nino | 1.04 | 0.856 | 1.27 | 0.686 | 1020 | ok | nb |
| fatal_wx | ga_piston | la_nina | 1.03 | 0.837 | 1.27 | 0.763 | 1020 | ok | nb |
| fatal_wx | helicopter | el_nino | 1.4 | 0.754 | 2.59 | 0.287 | 102 | ok | nb |
| fatal_wx | helicopter | la_nina | 0.989 | 0.489 | 2 | 0.976 | 102 | ok | nb |
| excl_ak_hi | airliner | el_nino | 0.853 | 0.599 | 1.21 | 0.378 | 295 | ok | nb |
| excl_ak_hi | airliner | la_nina | 0.794 | 0.529 | 1.19 | 0.265 | 295 | ok | nb |
| excl_ak_hi | charter | el_nino | 1.04 | 0.56 | 1.93 | 0.904 | 95 | ok | nb |
| excl_ak_hi | charter | la_nina | 0.98 | 0.49 | 1.96 | 0.955 | 95 | ok | nb |
| excl_ak_hi | ga_turbine | el_nino | 1.12 | 0.779 | 1.62 | 0.532 | 285 | ok | nb |
| excl_ak_hi | ga_turbine | la_nina | 1.2 | 0.798 | 1.79 | 0.386 | 285 | ok | nb |
| excl_ak_hi | ga_piston | el_nino | 1.02 | 0.922 | 1.12 | 0.733 | 4259 | ok | nb |
| excl_ak_hi | ga_piston | la_nina | 1.03 | 0.928 | 1.15 | 0.549 | 4259 | ok | nb |
| excl_ak_hi | helicopter | el_nino | 1.14 | 0.819 | 1.57 | 0.445 | 390 | ok | nb |
| excl_ak_hi | helicopter | la_nina | 1.46 | 1.04 | 2.04 | 0.0267 | 390 | ok | nb |
| super_level | airliner | el_nino | 0.749 | 0.469 | 1.2 | 0.226 | 308 | ok | nb |
| super_level | airliner | la_nina | 0.792 | 0.533 | 1.18 | 0.25 | 308 | ok | nb |
| super_level | airliner | super_el_nino | 1.12 | 0.683 | 1.84 | 0.653 | 308 | ok | nb |
| super_level | charter | el_nino | 0.947 | 0.569 | 1.58 | 0.836 | 195 | ok | nb |
| super_level | charter | la_nina | 0.953 | 0.583 | 1.56 | 0.846 | 195 | ok | nb |
| super_level | charter | super_el_nino | 0.797 | 0.372 | 1.71 | 0.559 | 195 | ok | nb |
| super_level | ga_turbine | el_nino | 1.35 | 0.86 | 2.12 | 0.192 | 295 | ok | poisson_boundary |
| super_level | ga_turbine | la_nina | 1.29 | 0.87 | 1.93 | 0.203 | 295 | ok | poisson_boundary |
| super_level | ga_turbine | super_el_nino | 0.783 | 0.449 | 1.37 | 0.389 | 295 | ok | poisson_boundary |
| super_level | ga_piston | el_nino | 1.02 | 0.91 | 1.15 | 0.712 | 4628 | ok | nb |
| super_level | ga_piston | la_nina | 1.02 | 0.918 | 1.13 | 0.718 | 4628 | ok | nb |
| super_level | ga_piston | super_el_nino | 0.987 | 0.842 | 1.16 | 0.876 | 4628 | ok | nb |
| super_level | helicopter | el_nino | 1.22 | 0.85 | 1.74 | 0.284 | 428 | ok | nb |
| super_level | helicopter | la_nina | 1.53 | 1.11 | 2.12 | 0.0104 | 428 | ok | nb |
| super_level | helicopter | super_el_nino | 0.909 | 0.512 | 1.61 | 0.744 | 428 | ok | nb |
| full_span | airliner | el_nino | 0.882 | 0.638 | 1.22 | 0.445 | 351 | ok | nb |
| full_span | airliner | la_nina | 0.811 | 0.561 | 1.17 | 0.268 | 351 | ok | nb |
| full_span | charter | el_nino | 0.898 | 0.584 | 1.38 | 0.624 | 195 | ok | nb |
| full_span | charter | la_nina | 0.933 | 0.578 | 1.5 | 0.775 | 195 | ok | nb |
| full_span | ga_turbine | el_nino | 1.08 | 0.794 | 1.48 | 0.613 | 391 | ok | nb |
| full_span | ga_turbine | la_nina | 1.09 | 0.762 | 1.55 | 0.643 | 391 | ok | nb |
| full_span | ga_piston | el_nino | 1 | 0.925 | 1.09 | 0.907 | 6429 | ok | nb |
| full_span | ga_piston | la_nina | 0.982 | 0.896 | 1.08 | 0.701 | 6429 | ok | nb |
| full_span | helicopter | el_nino | 1.02 | 0.784 | 1.34 | 0.864 | 613 | ok | nb |
| full_span | helicopter | la_nina | 1.41 | 1.06 | 1.87 | 0.019 | 613 | ok | nb |
| original_model | airliner | el_nino | 0.936 | 0.698 | 1.25 | 0.658 | 308 | ok | nb |
| original_model | airliner | la_nina | 0.846 | 0.634 | 1.13 | 0.254 | 308 | ok | nb |
| original_model | charter | el_nino | 0.917 | 0.683 | 1.23 | 0.566 | 195 | ok | nb |
| original_model | charter | la_nina | 0.884 | 0.669 | 1.17 | 0.387 | 195 | ok | nb |
| original_model | ga_turbine | el_nino | 0.961 | 0.73 | 1.27 | 0.779 | 295 | ok | nb |
| original_model | ga_turbine | la_nina | 1.04 | 0.678 | 1.6 | 0.853 | 295 | ok | nb |
| original_model | ga_piston | el_nino | 0.97 | 0.898 | 1.05 | 0.439 | 4628 | ok | nb |
| original_model | ga_piston | la_nina | 0.964 | 0.873 | 1.06 | 0.471 | 4628 | ok | nb |
| original_model | helicopter | el_nino | 1.1 | 0.791 | 1.52 | 0.577 | 428 | ok | nb |
| original_model | helicopter | la_nina | 1.2 | 0.931 | 1.54 | 0.161 | 428 | ok | nb |

## Limitations

- Flight-hour exposure is annual and national. The H1-N design compares months within the same year, so exposure errors can't bias it, but regional traffic isn't observed.
- The H1-R power figures assumed the tier's share of events (0.40, or a pessimistic 0.20); the shares weren't measured from the data.
- The power simulation assumed flat seasonality and Poisson month noise around year effects. That simplifies the fitted models.
- Counts are aircraft involvements, so a midair collision counts once per aircraft. "Fatal" is the event's highest injury.
- NTSB records from 2025 on are excluded because the cases are still being entered. Primary periods start in 1997 (airliners) or 2004 (all other types), after breaks in how flight hours were defined.
