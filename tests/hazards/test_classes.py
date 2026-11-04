import pandas as pd

AC = pd.DataFrame({"ev_id": ["E1"], "Aircraft_Key": [1]})


def _f(codes):
    return pd.DataFrame({"ev_id": "E1", "Aircraft_Key": 1, "finding_code": codes})


def _es(codes):
    return pd.DataFrame({"ev_id": "E1", "Aircraft_Key": 1, "Occurrence_Code": codes})


def _seq(pairs):
    return pd.DataFrame([("E1", 1, s, m) for s, m in pairs],
                        columns=["ev_id", "Aircraft_Key", "Subj_Code", "Modifier_Code"])


E_F, E_ES, E_SEQ = _f([]), _es([]), _seq([])


def _flags(findings=E_F, es=E_ES, seq=E_SEQ):
    from rime.hazards.classes import hazard_flags
    return hazard_flags(findings, es, seq, aircraft=AC).iloc[0]


def test_icing_post2008_finding():
    r = _flags(findings=_f(["0303102512"]))
    assert (r.icing, r.turbulence, r.convective) == (True, False, False)


def test_turbulence_excludes_wake():
    assert not _flags(findings=_f(["0303202544"])).turbulence


def test_convective_microburst_post2008():
    assert _flags(findings=_f(["0303405011"])).convective


def test_occurrence_last3_maps():
    assert _flags(es=_es([402210])).icing
    assert _flags(es=_es([404362])).turbulence
    assert _flags(es=_es([508390])).convective


def test_pre2008_modifiers():
    assert _flags(seq=_seq([(20000, 2213)])).icing
    assert _flags(seq=_seq([(20000, 2256)])).turbulence
    assert _flags(seq=_seq([(20000, 2208)])).convective
    r = _flags(seq=_seq([(20000, 2203)]))
    assert not (r.icing or r.turbulence or r.convective)


def _enroute(es=E_ES, occ=None):
    from rime.hazards.classes import enroute_flags
    occ = occ if occ is not None else pd.DataFrame(columns=["ev_id", "Aircraft_Key", "Phase_of_Flight"])
    return bool(enroute_flags(es, occ, aircraft=AC).iloc[0].enroute)


def test_enroute_post2008():
    assert _enroute(es=_es([402210])) is True
    assert _enroute(es=_es([508390])) is False
    assert _enroute(es=_es([453240])) is False  # maneuvering-hover is not en route


def test_enroute_pre2008():
    occ = lambda p: pd.DataFrame({"ev_id": ["E1"], "Aircraft_Key": [1], "Phase_of_Flight": [p]})
    assert _enroute(occ=occ(541)) is True
    assert _enroute(occ=occ(570)) is False


def _events(rows):
    return pd.DataFrame(rows, columns=["ev_id", "Aircraft_Key", "year", "ev_type", "category"])


def test_h3_counts_turbine_enroute_only():
    from rime.hazards.classes import hazard_counts
    ev = _events([("A", 1, 2010, "ACC", "ga_piston"), ("B", 1, 2010, "ACC", "airliner")])
    flags = pd.DataFrame({"ev_id": ["A", "B"], "Aircraft_Key": [1, 1], "icing": [True, True],
                          "turbulence": [False, False], "convective": [False, False]})
    enr = pd.DataFrame({"ev_id": ["A", "B"], "Aircraft_Key": [1, 1], "enroute": [True, True]})
    c = hazard_counts(ev, flags, enr).set_index(["year", "category", "hazard"])["count"]
    assert c[(2010, "ga_piston", "h3")] == 0
    assert c[(2010, "airliner", "h3")] == 1
    assert c[(2010, "ga_piston", "icing")] == 1


def test_counts_zero_filled():
    from rime.hazards.classes import hazard_counts
    ev = _events([("A", 1, 2010, "ACC", "ga_piston"), ("B", 1, 2011, "ACC", "airliner")])
    flags = pd.DataFrame({"ev_id": ["A", "B"], "Aircraft_Key": [1, 1], "icing": [True, False],
                          "turbulence": [False, False], "convective": [False, False]})
    enr = pd.DataFrame({"ev_id": ["A", "B"], "Aircraft_Key": [1, 1], "enroute": [False, False]})
    c = hazard_counts(ev, flags, enr).set_index(["year", "category", "hazard"])["count"]
    assert c[(2011, "ga_piston", "icing")] == 0
    assert c[(2010, "airliner", "turbulence")] == 0


def _occ(rows):
    return pd.DataFrame(rows, columns=["ev_id", "Aircraft_Key", "Occurrence_No", "Phase_of_Flight"])


def _seqn(rows):
    return pd.DataFrame(rows, columns=["ev_id", "Aircraft_Key", "Occurrence_No", "Subj_Code", "Modifier_Code"])


def _h3(findings=E_F, es=E_ES, seq=None, occ=None):
    from rime.hazards.classes import enroute_hazard_flags
    seq = seq if seq is not None else _seqn([])
    occ = occ if occ is not None else _occ([])
    return bool(enroute_hazard_flags(findings, es, seq, occ, aircraft=AC).iloc[0].enroute)


def test_h3_post2008_hazard_occurrence_must_be_enroute():
    assert _h3(es=_es([402210])) is True                 # icing in cruise
    assert _h3(es=_es([508390, 402240])) is False        # storm on approach + LOC in cruise


def test_h3_pre2008_links_hazard_to_its_occurrence_phase():
    seq = _seqn([("E1", 1, 2, 20000, 2213)])
    assert _h3(seq=seq, occ=_occ([("E1", 1, 1, 541), ("E1", 1, 2, 570)])) is False
    assert _h3(seq=seq, occ=_occ([("E1", 1, 1, 570), ("E1", 1, 2, 541)])) is True


def test_h3_findings_only_hazard_falls_back_to_any_enroute_occurrence():
    assert _h3(findings=_f(["0303102512"]), es=_es([402240])) is True


def test_pre2008_emergency_and_uncontrolled_descent_not_enroute():
    occ = lambda p: pd.DataFrame({"ev_id": ["E1"], "Aircraft_Key": [1], "Phase_of_Flight": [p]})
    assert _enroute(occ=occ(552)) is False and _enroute(occ=occ(553)) is False
