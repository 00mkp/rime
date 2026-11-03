import pandas as pd


def test_render_qa_sections():
    from rime.qa import render_qa
    events = pd.DataFrame({
        "ev_id": ["A", "B", "C"], "year": [2000, 2000, 2001], "ev_type": ["ACC"] * 3,
        "category": ["ga_piston"] * 3, "fatal": [False, True, False],
        "wx_involved": [True, False, False], "dec_latitude": [30.0, None, 31.0],
    })
    md = render_qa(events, {"non_us": 5, "pre_1990": 2})
    assert "## Rows dropped" in md and "| non_us | 5 |" in md
    assert "## Missing coordinates" in md and "| 2000 | 50.0% |" in md
    assert "## Accident counts by category and year" in md
    assert "oni" not in md.lower() and "el ni" not in md.lower()
