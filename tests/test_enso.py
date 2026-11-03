import pandas as pd
import pytest

from rime import paths


def _series(values, start="2000-01"):
    return pd.DataFrame({"month": pd.date_range(start, periods=len(values), freq="MS"),
                         "oni": values})


def test_five_season_run_is_el_nino():
    from rime.enso import label_phases
    out = label_phases(_series([0, 0.6, 0.7, 0.8, 0.9, 0.6, 0]))
    assert out["phase"].tolist() == ["neutral"] + ["el_nino"] * 5 + ["neutral"]
    assert out["episode_id"].iloc[1:6].nunique() == 1
    assert out["episode_id"].iloc[[0, 6]].isna().all()


def test_four_season_run_is_neutral():
    from rime.enso import label_phases
    out = label_phases(_series([0, 0.6, 0.7, 0.8, 0.9, 0]))
    assert (out["phase"] == "neutral").all()


def test_la_nina_run():
    from rime.enso import label_phases
    out = label_phases(_series([0, -0.5, -0.9, -1.2, -0.8, -0.5, 0]))
    assert out["phase"].tolist() == ["neutral"] + ["la_nina"] * 5 + ["neutral"]


def test_super_flag_on_peak_ge_2():
    from rime.enso import label_phases
    out = label_phases(_series([0, 0.8, 1.5, 2.1, 1.5, 0.8, 0, 0.8, 1.2, 1.9, 1.2, 0.8, 0]))
    assert out["super"].iloc[1:6].all()
    assert not out["super"].iloc[7:12].any()
    assert not out["super"].iloc[[0, 6, 12]].any()


def test_trailing_short_run_is_provisional():
    from rime.enso import label_phases
    out = label_phases(_series([0, 0, 0, 1.4, 1.8, 2.2]))
    assert out["phase"].iloc[3:].eq("el_nino").all()
    assert out["provisional"].iloc[3:].all()
    assert out["super"].iloc[3:].all()
    assert not out["provisional"].iloc[:3].any()


def test_completed_trailing_run_not_provisional():
    from rime.enso import label_phases
    out = label_phases(_series([0, 0.6, 0.7, 0.8, 0.9, 0.6]))
    assert out["phase"].iloc[1:].eq("el_nino").all()
    assert not out["provisional"].any()


def test_parse_oni_center_month():
    from rime.enso import parse_oni
    text = " SEAS  YR   TOTAL   ANOM\n  DJF 1950  25.01  -1.32\n  NDJ 1950  25.40  -0.84\n"
    out = parse_oni(text)
    assert out["month"].tolist() == [pd.Timestamp("1950-01-01"), pd.Timestamp("1950-12-01")]
    assert out["oni"].tolist() == [-1.32, -0.84]


@pytest.mark.slow
def test_real_oni_known_episodes():
    from rime.enso import label_phases, parse_oni
    raw = paths.RAW / "oni.ascii.txt"
    if not raw.exists():
        pytest.skip("ONI not downloaded")
    out = label_phases(parse_oni(raw.read_text())).set_index("month")
    for m in ["1997-12-01", "2015-12-01"]:
        assert out.loc[m, "phase"] == "el_nino" and bool(out.loc[m, "super"])
    assert out.loc["2010-12-01", "phase"] == "la_nina"
