import math

import pytest

CASES = [
    ("The airplane was cruising at FL350 when the crew reported icing.", 35000, "fl"),
    ("The pilot reported flight level 240 to ATC.", 24000, "fl"),
    ("at an altitude of about 2,500 feet msl the engine lost power", 2500, "msl"),
    ("the airplane descended through 11,000 ft agl rapidly", 11000, "agl"),
    ("leveled off at 8,500 feet before the turn", 8500, "unspecified"),
    ("at an altitude of 6000 feet mean sea level (MSL), the pilot radioed", 6000, "msl"),
    ("at an altitude of about 900 feet above ground level the engine quit", 900, "agl"),
]
REJECT = [
    "the airplane landed on the 5,000-foot runway",
    "the airport's field elevation 6,500 feet msl",
    "visibility of 1,500 feet in fog",
    "the ceiling was 1,200 feet agl",
    "climbing through an altitude of 75,000 feet",
    "The traffic pattern altitude at Scottsdale is 2,500 feet MSL.",
    "The pilot filed for an en route altitude of 20,000 feet msl.",
    "an AIRMET for occasional moderate turbulence below 8,000 feet msl",
    "cloud tops were reported at 12,000 feet msl",
    "the freezing level was about 9,000 feet msl",
    None,
    "",
]


@pytest.mark.parametrize("text,ft,ref", CASES)
def test_extracts(text, ft, ref):
    from rime.catalog.altitude import extract_altitude
    a, r, span = extract_altitude(text)
    assert a == ft and r == ref and len(span) > 0 and span in text


@pytest.mark.parametrize("text", REJECT)
def test_rejects(text):
    from rime.catalog.altitude import extract_altitude
    a, r, span = extract_altitude(text)
    assert math.isnan(a) and r == "" and span == ""
