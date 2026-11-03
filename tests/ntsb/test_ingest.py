import pandas as pd
import pytest

from rime import paths


def test_combine_prefers_avall_on_overlap():
    from rime.ntsb.ingest import combine
    avall = pd.DataFrame({"ev_id": ["A", "B"], "x": [1, 2]})
    pre = pd.DataFrame({"ev_id": ["B", "C"], "x": [20, 30]})
    out = combine(avall, pre).sort_values("ev_id").reset_index(drop=True)
    assert out["ev_id"].tolist() == ["A", "B", "C"]
    assert out.loc[out.ev_id == "B", "source_db"].tolist() == ["avall"]
    assert out.loc[out.ev_id == "B", "x"].tolist() == [2]


def test_combine_handles_child_tables():
    from rime.ntsb.ingest import combine
    avall = pd.DataFrame({"ev_id": ["B", "B"], "finding_no": [1, 2]})
    pre = pd.DataFrame({"ev_id": ["B", "B"], "finding_no": [1, 2]})
    out = combine(avall, pre)
    assert len(out) == 2
    assert set(out["source_db"]) == {"avall"}


@pytest.mark.slow
def test_read_mdb_table_real_file():
    from rime.ntsb.ingest import read_mdb_table
    mdb = paths.RAW / "avall.mdb"
    if not mdb.exists():
        pytest.skip("avall.mdb not downloaded")
    ev = read_mdb_table(mdb, "events")
    for col in ["ev_id", "ev_date", "dec_latitude", "dec_longitude", "ev_state",
                "ev_country", "ev_highest_injury", "wx_cond_basic"]:
        assert col in ev.columns
    assert len(ev) > 25_000
