import json

import pytest


class FakeClient:
    def __init__(self, payload=b"CDF"):
        self.calls, self.payload = [], payload

    def retrieve(self, name, request, target):
        self.calls.append((name, request, target))
        with open(target, "wb") as f:
            f.write(self.payload)


@pytest.fixture
def tmp_paths(tmp_path, monkeypatch):
    from rime import paths
    monkeypatch.setattr(paths, "RAW", tmp_path / "raw")
    monkeypatch.setattr(paths, "PROCESSED", tmp_path / "processed")
    return tmp_path


def test_request_parts_and_levels():
    from rime.era5.download import ICING_LEVELS, requests_for_month
    parts = requests_for_month(2005, 3)
    assert set(parts) == {"pl_icing", "pl_upper", "sl_cape", "sl_cp", "sl_cp_prev"}
    name, req = parts["pl_icing"]
    assert name == "reanalysis-era5-pressure-levels"
    assert req["pressure_level"] == [str(p) for p in ICING_LEVELS]
    assert ICING_LEVELS == (850, 825, 800, 775, 750, 700, 650, 600, 550, 500, 450, 400)
    assert req["time"] == ["00:00", "06:00", "12:00", "18:00"] and len(req["day"]) == 31
    assert req["area"] == [50, -125, 24, -66]
    _, cp = parts["sl_cp"]
    assert len(cp["time"]) == 24
    _, prev = parts["sl_cp_prev"]
    assert (prev["year"], prev["month"], prev["day"]) == (["2005"], ["02"], ["28"])
    assert prev["time"] == ["19:00", "20:00", "21:00", "22:00", "23:00"]


def test_request_january_uses_previous_december():
    from rime.era5.download import requests_for_month
    _, prev = requests_for_month(1990, 1)["sl_cp_prev"]
    assert (prev["year"], prev["month"], prev["day"]) == (["1989"], ["12"], ["31"])


def test_download_writes_parts_atomically(tmp_paths):
    from rime.era5.download import download_month
    files = download_month(2005, 3, client=FakeClient())
    assert len(files) == 5 and all(p.exists() and p.suffix == ".nc" for p in files.values())
    assert not list((tmp_paths / "raw" / "era5" / "2005-03").glob("*.part"))


def test_partial_file_is_retried(tmp_paths):
    from rime.era5.download import download_month
    d = tmp_paths / "raw" / "era5" / "2005-03"
    d.mkdir(parents=True)
    (d / "sl_cape.nc.part").write_bytes(b"half")
    c = FakeClient()
    download_month(2005, 3, client=c)
    assert any(t.endswith("sl_cape.nc.part") for _, _, t in c.calls)
    assert (d / "sl_cape.nc").read_bytes() == b"CDF"


def test_complete_part_not_redownloaded(tmp_paths):
    from rime.era5.download import download_month
    download_month(2005, 3, client=FakeClient())
    c = FakeClient()
    download_month(2005, 3, client=c)
    assert c.calls == []


def test_months_todo_skips_done(tmp_paths):
    from rime.era5.download import months_todo
    (tmp_paths / "processed").mkdir()
    (tmp_paths / "processed" / "era5_manifest.json").write_text(json.dumps({"1990-01": {"status": "done"},
                                                                           "1990-02": {"status": "failed:x"}}))
    todo = months_todo((1990, 1), (1990, 3))
    assert todo == [(1990, 2), (1990, 3)]
