import pandas as pd
import pytest

from rime import paths

E = pd.DataFrame(columns=["ev_id", "Aircraft_Key"])


def _f(rows):
    return pd.DataFrame(rows, columns=["ev_id", "Aircraft_Key", "finding_code"])


def _occ(rows):
    return pd.DataFrame(rows, columns=["ev_id", "Aircraft_Key", "Occurrence_Code"])


def _seq(rows):
    return pd.DataFrame(rows, columns=["ev_id", "Aircraft_Key", "Subj_Code", "Modifier_Code"])


def _evseq(rows):
    return pd.DataFrame(rows, columns=["ev_id", "Aircraft_Key", "Occurrence_Code"])


def _run(findings=None, occ=None, seq=None, aircraft=None, evseq=None):
    from rime.ntsb.weather_flags import weather_flags
    aircraft = aircraft if aircraft is not None else pd.DataFrame(
        {"ev_id": ["E1"], "Aircraft_Key": [1]})
    out = weather_flags(
        findings if findings is not None else _f([]),
        evseq if evseq is not None else _evseq([]),
        occ if occ is not None else _occ([]),
        seq if seq is not None else _seq([]),
        aircraft=aircraft,
    )
    return out.set_index(["ev_id", "Aircraft_Key"])


def test_post2008_wind_finding_flags():
    out = _run(findings=_f([("E1", 1, "0303401234")]))
    assert bool(out.loc[("E1", 1), "wx_involved"]) is True
    assert "0303401234" in out.loc[("E1", 1), "wx_basis"]


def test_post2008_light_condition_not_weather():
    out = _run(findings=_f([("E1", 1, "0303601234")]))
    assert bool(out.loc[("E1", 1), "wx_involved"]) is False


def test_pre2008_occurrence_240_flags():
    out = _run(occ=_occ([("E1", 1, 240)]))
    assert bool(out.loc[("E1", 1), "wx_involved"]) is True


def test_pre2008_subj_icing_flags():
    out = _run(seq=_seq([("E1", 1, 20000, 2213)]))
    assert bool(out.loc[("E1", 1), "wx_involved"]) is True
    assert "20000/2213" in out.loc[("E1", 1), "wx_basis"]


def test_wake_turbulence_not_weather():
    out = _run(seq=_seq([("E1", 1, 24715, 0)]), occ=_occ([("E1", 1, 410)]))
    assert bool(out.loc[("E1", 1), "wx_involved"]) is False


def test_aircraft_without_any_codes_is_false():
    out = _run(aircraft=pd.DataFrame({"ev_id": ["E1", "E2"], "Aircraft_Key": [1, 1]}),
               findings=_f([("E1", 1, "0303401234")]))
    assert bool(out.loc[("E2", 1), "wx_involved"]) is False
    assert out.loc[("E2", 1), "wx_basis"] == ""


def test_flags_attach_to_the_right_aircraft():
    out = _run(aircraft=pd.DataFrame({"ev_id": ["E1", "E1"], "Aircraft_Key": [1, 2]}),
               findings=_f([("E1", 2, "0303201111")]))
    assert bool(out.loc[("E1", 1), "wx_involved"]) is False
    assert bool(out.loc[("E1", 2), "wx_involved"]) is True


@pytest.mark.slow
def test_real_data_weather_share_positive_every_year():
    from rime.ntsb.weather_flags import build_flags_from_interim
    d = paths.INTERIM / "ntsb"
    if not (d / "events.parquet").exists():
        pytest.skip("NTSB not ingested")
    flags = build_flags_from_interim()
    ev = pd.read_parquet(d / "events.parquet", columns=["ev_id", "ev_year", "ev_type"])
    m = flags.merge(ev, on="ev_id")
    m = m[(m.ev_type == "ACC") & m.ev_year.between(1990, 2025)]
    share = m.groupby("ev_year")["wx_involved"].mean()
    assert len(share) == 36
    assert (share > 0).all()


def test_post2008_wake_turbulence_not_weather():
    out = _run(findings=_f([("E1", 1, "0303202544")]))
    assert bool(out.loc[("E1", 1), "wx_involved"]) is False


def test_post2008_clear_air_turbulence_is_weather():
    out = _run(findings=_f([("E1", 1, "0303201544")]))
    assert bool(out.loc[("E1", 1), "wx_involved"]) is True


def test_post2008_weather_occurrence_flags():
    # Events_Sequence code = 3-digit phase + 3-digit occurrence; 210 = structural icing
    out = _run(evseq=_evseq([("E1", 1, 402210)]))
    assert bool(out.loc[("E1", 1), "wx_involved"]) is True
    assert "seq402210" in out.loc[("E1", 1), "wx_basis"]


def test_post2008_wake_occurrence_not_weather():
    out = _run(evseq=_evseq([("E1", 1, 404361)]))
    assert bool(out.loc[("E1", 1), "wx_involved"]) is False


def test_pre2008_weather_subject_with_light_modifier_not_weather():
    out = _run(seq=_seq([("E1", 1, 20000, 2302)]))
    assert bool(out.loc[("E1", 1), "wx_involved"]) is False
