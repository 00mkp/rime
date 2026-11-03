import pandas as pd

COLS = ["family", "test", "category", "phase", "rr", "ci_lo", "ci_hi", "p", "p_holm", "reject",
        "n_events", "status", "model"]


def _conf(rows):
    return pd.DataFrame(rows, columns=COLS)


SENS = pd.DataFrame(columns=["sensitivity", "category", "phase", "rr", "ci_lo", "ci_hi", "p",
                             "n_events", "status", "model"])
META = {"prereg_sha": "abc", "run_at_utc": "2026-11-02T00:00:00+00:00", "periods": {}}


def test_summary_reports_rejection_in_words():
    from rime.h1.summary import render_summary
    conf = _conf([("H1-N", "ga_piston el_nino", "ga_piston", "el_nino", 1.18, 1.06, 1.31, 0.001, 0.009,
                   True, 4000, "ok", "nb")])
    md = render_summary(conf, _conf([]), SENS, META)
    assert "18% more" in md and "6–31%" in md


def test_summary_null_wording():
    from rime.h1.summary import render_summary
    conf = _conf([("H1-N", "airliner la_nina", "airliner", "la_nina", 0.9, 0.7, 1.2, 0.4, 1.0,
                   False, 300, "ok", "nb")])
    assert "no detectable relationship" in render_summary(conf, _conf([]), SENS, META)


def test_summary_flags_negative_control():
    from rime.h1.summary import render_summary
    nc = _conf([("NC", "helicopter el_nino", "helicopter", "el_nino", 1.3, 1.1, 1.5, 0.001, 0.009,
                 True, 900, "ok", "nb")])
    md = render_summary(_conf([]), nc, SENS, META)
    assert "could hide or mimic a weather effect" in md  # H1-N for helicopter was not significant
    conf = _conf([("H1-N", "helicopter el_nino", "helicopter", "el_nino", 1.3, 1.1, 1.5, 0.001, 0.009,
                   True, 400, "ok", "nb")])
    assert "may reflect something other than weather" in render_summary(conf, nc, SENS, META)


def test_summary_nominal_but_not_after_correction():
    from rime.h1.summary import render_summary
    conf = _conf([("H1-N", "helicopter la_nina", "helicopter", "la_nina", 1.5, 1.09, 2.07, 0.014, 0.12,
                   False, 428, "ok", "nb")])
    md = render_summary(conf, _conf([]), SENS, META)
    assert "no detectable relationship after correction" in md
    assert "nominally 50% more" in md.lower()


def test_summary_h1r_opposite_direction_and_capitalization():
    from rime.h1.summary import render_summary
    conf = _conf([("H1-R", "H1-Rb ga_piston northern tier share, la_nina winters", "ga_piston", "la_nina",
                   0.71, 0.53, 0.94, 0.99, 0.99, False, 1000, "ok", "nb")])
    md = render_summary(conf, _conf([]), SENS, META)
    assert "no detectable relationship after correction" in md
    assert "opposite to the predicted direction" in md
    assert "rule out the predicted increase" in md
    assert "La Niña winters" in md and "la niña" not in md


def test_summary_nc_lists_nominal_rows_without_overclaiming():
    from rime.h1.summary import render_summary
    nc = _conf([("NC", "ga_piston la_nina", "ga_piston", "la_nina", 1.08, 1.02, 1.14, 0.006, 0.055,
                 False, 9000, "ok", "nb")])
    md = render_summary(_conf([]), nc, SENS, META)
    assert "No negative-control test was significant after Holm correction" in md
    assert "doesn't shift non-weather accidents, as expected" not in md
    assert "ga_piston la_nina" in md.split("## Negative control")[1].split("## Sensitivity")[0]
    assert "8% more" in md


def test_summary_states_no_cross_family_correction_and_exposure_caveat():
    from rime.h1.summary import render_summary
    md = render_summary(_conf([]), _conf([]), SENS, META)
    assert "no correction across families" in md
    assert "errors in annual exposure" in md and "can't bias" not in md
