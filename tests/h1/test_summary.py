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
    assert "may reflect something other than weather" in md


def test_summary_nominal_but_not_after_correction():
    from rime.h1.summary import render_summary
    conf = _conf([("H1-N", "helicopter la_nina", "helicopter", "la_nina", 1.5, 1.09, 2.07, 0.014, 0.12,
                   False, 428, "ok", "nb")])
    md = render_summary(conf, _conf([]), SENS, META)
    assert "not significant after correcting for multiple tests" in md
    assert "no detectable relationship" not in md


def test_summary_h1r_opposite_direction_and_capitalization():
    from rime.h1.summary import render_summary
    conf = _conf([("H1-R", "H1-Rb ga_piston northern tier share, la_nina winters", "ga_piston", "la_nina",
                   0.71, 0.53, 0.94, 0.99, 0.99, False, 1000, "ok", "nb")])
    md = render_summary(conf, _conf([]), SENS, META)
    assert "opposite to the predicted direction" in md
    assert "La Niña winters" in md and "la niña" not in md
