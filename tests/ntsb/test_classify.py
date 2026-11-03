import csv

import pytest

from rime import paths


@pytest.mark.parametrize("country,state,expected", [
    ("USA", "FL", "southeast"),
    ("USA", "AK", "alaska"),
    ("USA", "HI", "hawaii"),
    ("USA", "TX", "south"),
    ("USA", "PR", "excluded_location"),
    ("USA", None, "excluded_location"),
    ("CAN", "ON", "excluded_location"),
    (None, "FL", "excluded_location"),
])
def test_region_for(country, state, expected):
    from rime.ntsb.classify import region_for
    assert region_for(country, state) == expected


@pytest.mark.parametrize("cat,part,eng,unmanned,expected", [
    ("AIR", "121", "TF", "N", "airliner"),
    ("AIR", "135", "TF", "N", "charter"),
    ("HELI", "135", "TS", "N", "helicopter"),
    ("HELI", "121", "TS", "N", None),
    ("AIR", "091", "REC", "N", "ga_piston"),
    ("AIR", "091", "TF", "N", "ga_turbine"),
    ("AIR", "137", "TP", "N", "ga_turbine"),
    ("AIR", "091", "REC", "Y", None),
    ("AIR", "091", "REC", True, None),
    ("AIR", "091", "REC", False, "ga_piston"),
    ("GLI", "091", None, "N", None),
    ("AIR", "129", "TF", "N", None),
    ("AIR", "091", None, "N", None),
    ("AIR", "91", "REC", "N", "ga_piston"),
    (" air ", " 091 ", "rec", "N", "ga_piston"),
])
def test_category_for(cat, part, eng, unmanned, expected):
    from rime.ntsb.classify import category_for
    assert category_for(cat, part, eng, unmanned) == expected


@pytest.mark.parametrize("cat,part,eng,expected", [
    ("AIR", "091", "TF", True),
    ("AIR", "135", "TJ", True),
    ("AIR", "121", "TF", False),
    ("AIR", "091", "TP", False),
    ("HELI", "091", "TS", False),
])
def test_is_business_jet(cat, part, eng, expected):
    from rime.ntsb.classify import is_business_jet
    assert is_business_jet(cat, part, eng) is expected


def test_regions_csv_covers_50_states_plus_dc():
    with (paths.MANUAL / "regions.csv").open() as f:
        states = {row["state"] for row in csv.DictReader(f)}
    assert len(states) == 51
