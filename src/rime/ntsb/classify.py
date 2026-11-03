"""Region (NCEI climate regions + AK/HI) and aircraft category rules from the spec."""
import csv
from functools import cache

from rime import paths

EXCLUDED_LOCATION = "excluded_location"
CATEGORIES = ("airliner", "charter", "ga_turbine", "ga_piston", "helicopter")
GA_PARTS = {"091", "091K", "091F", "125", "133", "137"}
TURBINE = {"TF", "TJ", "TP", "TS", "GTFN"}
PISTON = {"REC", "ELEC"}
JET = {"TF", "TJ", "GTFN"}


def _norm(v) -> str | None:
    if v is None or (isinstance(v, float) and v != v):
        return None
    s = str(v).strip().upper()
    return s or None


def _norm_part(v) -> str | None:
    s = _norm(v)
    if s and s[0].isdigit():
        digits = "".join(c for c in s if c.isdigit())
        return digits.zfill(3) + s[len(digits):]
    return s


@cache
def _state_regions() -> dict[str, str]:
    with (paths.MANUAL / "regions.csv").open() as f:
        return {r["state"]: r["region"] for r in csv.DictReader(f)}


def region_for(ev_country, ev_state) -> str:
    if _norm(ev_country) != "USA":
        return EXCLUDED_LOCATION
    return _state_regions().get(_norm(ev_state), EXCLUDED_LOCATION)


def _is_unmanned(v) -> bool:
    return v is True or _norm(v) in {"Y", "TRUE"}


def category_for(acft_category, far_part, eng_type, unmanned) -> str | None:
    if _is_unmanned(unmanned):
        return None
    cat, part, eng = _norm(acft_category), _norm_part(far_part), _norm(eng_type)
    if cat == "HELI":
        return None if part == "121" else "helicopter"
    if cat != "AIR":
        return None
    if part == "121":
        return "airliner"
    if part == "135":
        return "charter"
    if part in GA_PARTS:
        if eng in TURBINE:
            return "ga_turbine"
        if eng in PISTON:
            return "ga_piston"
    return None


def is_business_jet(acft_category, far_part, eng_type) -> bool:
    return (_norm(acft_category) == "AIR" and _norm(eng_type) in JET
            and _norm_part(far_part) in {"091", "091K", "135"})
