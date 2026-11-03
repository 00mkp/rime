import pandas as pd


def _inputs():
    events = pd.DataFrame({
        "ev_id": ["E1", "E2", "E3", "E4"],
        "ev_date": pd.to_datetime(["2015-06-01", "2015-07-01", "1985-01-01", "2016-01-01"]),
        "ev_type": ["ACC", "ACC", "ACC", "ACC"],
        "ev_country": ["USA", "USA", "USA", "USA"],
        "ev_state": ["FL", "PR", "TX", "CO"],
        "ev_highest_injury": ["FATL", "NONE", "NONE", "SERS"],
        "dec_latitude": [26.6, 18.4, 30.0, 39.7],
        "dec_longitude": [-80.1, -66.0, -97.0, -105.0],
        "wx_cond_basic": ["IMC", "VMC", "VMC", "VMC"],
        "source_db": ["avall"] * 4,
    })
    aircraft = pd.DataFrame({
        "ev_id": ["E1", "E1", "E2", "E3", "E4"],
        "Aircraft_Key": [1, 2, 1, 1, 1],
        "acft_category": ["AIR", "AIR", "AIR", "AIR", "GLI"],
        "far_part": ["121", "091", "091", "091", "091"],
        "unmanned": [False] * 5,
    })
    engines = pd.DataFrame({
        "ev_id": ["E1", "E1", "E1", "E2", "E3"],
        "Aircraft_Key": [1, 1, 2, 1, 1],
        "eng_no": [1, 2, 1, 1, 1],
        "eng_type": ["TF", "TF", "REC", "REC", "REC"],
    })
    flags = pd.DataFrame({
        "ev_id": ["E1", "E1", "E2", "E3", "E4"],
        "Aircraft_Key": [1, 2, 1, 1, 1],
        "wx_involved": [True, False, False, False, False],
        "wx_basis": ["0303201111", "", "", "", ""],
    })
    return events, aircraft, engines, flags


def test_midair_two_aircraft_two_rows():
    from rime.ntsb.events import assemble, counts_by_category_year
    out, _ = assemble(*_inputs())
    e1 = out[out.ev_id == "E1"].set_index("Aircraft_Key")
    assert len(e1) == 2
    assert e1.loc[1, "category"] == "airliner" and e1.loc[2, "category"] == "ga_piston"
    c = counts_by_category_year(out).set_index(["year", "category"])
    assert c.loc[(2015, "airliner"), "accidents"] == 1
    assert c.loc[(2015, "ga_piston"), "accidents"] == 1
    assert c.loc[(2015, "airliner"), "wx_accidents"] == 1
    assert c.loc[(2015, "airliner"), "fatal_wx_accidents"] == 1
    assert c.loc[(2015, "ga_piston"), "wx_accidents"] == 0


def test_excluded_location_dropped_and_reported():
    from rime.ntsb.events import assemble
    out, drops = assemble(*_inputs())
    assert "E2" not in set(out.ev_id)
    assert drops.get("excluded_location", 0) == 1
    assert drops.get("pre_1990", 0) == 1
    assert drops.get("out_of_scope_category", 0) == 1


def test_no_enso_columns_before_prereg():
    from rime.ntsb.events import assemble
    out, _ = assemble(*_inputs())
    assert not [c for c in out.columns if any(k in c.lower() for k in ("oni", "phase", "enso"))]
