import pandas as pd
import pytest

HEADER = "year,category,flight_hours,departures,source,source_url\n"


def _csv(tmp_path, body):
    p = tmp_path / "exposure.csv"
    p.write_text(HEADER + body)
    return p


def test_load_exposure_rejects_unknown_category(tmp_path):
    from rime.exposure import load_exposure
    with pytest.raises(ValueError, match="category"):
        load_exposure(_csv(tmp_path, "2000,blimp,100,,x,u\n"))


def test_load_exposure_rejects_nonpositive_hours(tmp_path):
    from rime.exposure import load_exposure
    with pytest.raises(ValueError, match="flight_hours"):
        load_exposure(_csv(tmp_path, "2000,airliner,0,10,x,u\n"))


def test_load_exposure_rejects_duplicates(tmp_path):
    from rime.exposure import load_exposure
    with pytest.raises(ValueError, match="duplicate"):
        load_exposure(_csv(tmp_path, "2000,airliner,5,1,x,u\n2000,airliner,6,1,x,u\n"))


def test_load_exposure_reads_valid_rows(tmp_path):
    from rime.exposure import load_exposure
    df = load_exposure(_csv(tmp_path, "2000,airliner,5,1,x,u\n2001,ga_piston,7,,y,v\n"))
    assert df["flight_hours"].tolist() == [5.0, 7.0]
    assert pd.isna(df.loc[1, "departures"])


def test_rate_frame_drops_missing_years():
    from rime.exposure import rate_frame
    counts = pd.DataFrame({"year": [1995, 1996], "category": ["ga_piston"] * 2, "wx_accidents": [3, 4]})
    exposure = pd.DataFrame({"year": [1996], "category": ["ga_piston"], "flight_hours": [1e6],
                             "departures": [None], "source": ["s"], "source_url": ["u"]})
    joined, dropped = rate_frame(counts, exposure)
    assert joined["year"].tolist() == [1996]
    assert joined["flight_hours"].tolist() == [1e6]
    assert list(dropped[["year", "category"]].itertuples(index=False, name=None)) == [(1995, "ga_piston")]


def test_committed_exposure_is_valid():
    from rime.exposure import load_exposure, CATEGORIES
    df = load_exposure()
    for cat in CATEGORIES:
        years = sorted(df.loc[df.category == cat, "year"])
        assert years, f"no exposure for {cat}"
        # FAA ran no GA survey for 2011, so allow single missing years
        gaps = [b - a for a, b in zip(years, years[1:])]
        assert len(years) >= 15, f"{cat}: only {len(years)} years"
        assert max(gaps, default=1) <= 2, f"{cat}: gap of {max(gaps)} years"
        assert years[-1] >= 2023, f"{cat}: ends {years[-1]}"
