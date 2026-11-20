import pandas as pd

EA_COLS = ["ev_id", "Aircraft_Key", "ev_type", "highest_injury", "fatal", "year", "dec_latitude", "dec_longitude",
           "region", "category", "is_business_jet", "source_db", "wx_involved", "wx_basis", "wx_cond_basic"]


def _inputs(time=2350.0, date="2005-12-31", tz="UTC", es_rows=(), occ_rows=(), narr="cruising at FL350 when"):
    ea = pd.DataFrame([("E1", 1, "ACC", "FATL", True, int(date[:4]), 30.0, -90.0, "south", "ga_piston", False, "avall",
                        True, "x", "IMC"),
                       ("E2", 1, "ACC", "MINR", False, 2005, 30.0, -90.0, "south", "ga_piston", False, "avall",
                        False, "", "VMC"),
                       ("E3", 1, "INC", "FATL", True, 2005, 30.0, -90.0, "south", "ga_piston", False, "avall",
                        False, "", "VMC")], columns=EA_COLS)
    ev = pd.DataFrame({"ev_id": ["E1", "E2", "E3"], "ntsb_no": ["N1", "N2", "N3"], "ev_date": [date] * 3,
                       "ev_time": [time] * 3, "ev_tmzn": [tz] * 3, "light_cond": ["NITE"] * 3})
    es = pd.DataFrame(list(es_rows), columns=["ev_id", "Aircraft_Key", "Occurrence_Code", "Occurrence_Description", "Defining_ev"])
    occ = pd.DataFrame(list(occ_rows), columns=["ev_id", "Aircraft_Key", "Occurrence_No", "Occurrence_Code", "Phase_of_Flight"])
    narr_df = pd.DataFrame({"ev_id": ["E1"], "Aircraft_Key": [1], "narr_accf": [narr], "narr_accp": [None],
                            "narr_cause": ["probable cause text"]})
    ct = pd.DataFrame({"code": ["240", "230"], "meaning": ["IN FLIGHT ENCOUNTER WITH WEATHER", "LOSS OF CONTROL - IN FLIGHT"]})
    return ea, ev, es, occ, narr_df, ct


def _row(**kw):
    from rime.catalog.build import build_catalog
    cat = build_catalog(*_inputs(**kw))
    return cat, cat.set_index("ev_id").loc["E1"]


def test_literal_time_and_scope():
    cat, r = _row()
    assert r.time_utc == pd.Timestamp("2005-12-31 23:50") and list(cat.ev_id) == ["E1"]


def test_invalid_time_and_non_utc():
    assert _row(time=2460.0)[1].time_flag == "no_time"
    assert _row(time=975.0)[1].time_flag == "no_time"
    _, r = _row(tz="EST")
    assert r.time_flag == "no_time" and pd.isna(r.time_utc)


def test_post2008_defining_event_phase():
    _, r = _row(es_rows=[("E1", 1, 402240, "Enroute-cruise Loss of control in flight", True),
                         ("E1", 1, 550090, "Landing Other", False)])
    assert r.phase == "cruise" and r.defining_event == "Enroute-cruise Loss of control in flight"


def test_pre2008_first_occurrence_phase():
    _, r = _row(occ_rows=[("E1", 1, 2, 240, 570), ("E1", 1, 1, 230, 541)])
    assert r.phase == "cruise" and r.defining_event == "LOSS OF CONTROL - IN FLIGHT"


def test_no_occurrences_unknown_kept():
    _, r = _row()
    assert r.phase == "unknown" and r.defining_event == ""


def test_altitude_and_forbidden_columns():
    cat, r = _row()
    assert r.altitude_ft == 35000 and r.altitude_ref == "fl"
    assert not [c for c in cat.columns if any(k in c.lower() for k in ("wx_", "finding", "cause"))]


def test_summary_states_altitude_caveat():
    from rime.catalog.build import build_catalog, render_summary
    md = render_summary(build_catalog(*_inputs()))
    assert "not necessarily the altitude at the moment of the accident" in md


def test_unchecked_when_no_daynight_info():
    import numpy as np
    from rime.catalog.build import build_catalog
    ea, ev, es, occ, narr, ct = _inputs(time=1200.0)
    ev["light_cond"] = "DUSK"
    r = build_catalog(ea, ev, es, occ, narr, ct).set_index("ev_id").loc["E1"]
    assert r.time_flag == "unchecked"


def test_weather_defining_events_withheld():
    _, r = _row(es_rows=[("E1", 1, 450401, "Maneuvering VFR encounter with IMC", True)])
    assert r.defining_event == "" and r.phase == "maneuvering"
    _, r = _row(occ_rows=[("E1", 1, 1, 240, 541)])
    assert r.defining_event == "" and r.phase == "cruise"


def test_summary_tables_and_time_caveats():
    from rime.catalog.build import build_catalog, render_summary
    md = render_summary(build_catalog(*_inputs()))
    assert "## Coverage by aircraft category" in md and "## Phase by source database" in md
    assert "lower bound" in md and "24-hour" in md
