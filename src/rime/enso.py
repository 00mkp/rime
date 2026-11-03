"""NOAA CPC Oceanic Niño Index (ONI) and ENSO phase labels per month."""
import numpy as np
import pandas as pd

from rime import paths
from rime.cli import register
from rime.download import fetch

ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
SEASONS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
THRESHOLD = 0.5
MIN_RUN = 5
SUPER = 2.0


def parse_oni(text: str) -> pd.DataFrame:
    """Each 3-month season is assigned to its center month (DJF→Jan … NDJ→Dec)."""
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 4 and parts[0] in SEASONS:
            month = SEASONS.index(parts[0]) + 1
            rows.append((pd.Timestamp(int(parts[1]), month, 1), float(parts[3])))
    return pd.DataFrame(rows, columns=["month", "oni"])


def label_phases(oni: pd.DataFrame) -> pd.DataFrame:
    """CPC rule: ≥5 consecutive seasons at ≥+0.5 is El Niño, ≤−0.5 La Niña, else neutral.

    A run that reaches the end of the record but is shorter than 5 seasons is
    labeled by its sign with provisional=True (the episode may still qualify).
    """
    out = oni.sort_values("month").reset_index(drop=True).copy()
    v = out["oni"].to_numpy()
    sign = np.where(v >= THRESHOLD, 1, np.where(v <= -THRESHOLD, -1, 0))
    phase = np.full(len(v), "neutral", dtype=object)
    episode = np.full(len(v), np.nan)
    sup = np.zeros(len(v), dtype=bool)
    prov = np.zeros(len(v), dtype=bool)
    ep = 0
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and sign[j + 1] == sign[i]:
            j += 1
        length = j - i + 1
        at_end = j == len(v) - 1
        if sign[i] != 0 and (length >= MIN_RUN or at_end):
            phase[i:j + 1] = "el_nino" if sign[i] > 0 else "la_nina"
            episode[i:j + 1] = ep
            ep += 1
            prov[i:j + 1] = length < MIN_RUN
            if sign[i] > 0 and v[i:j + 1].max() >= SUPER:
                sup[i:j + 1] = True
        i = j + 1
    out["phase"] = phase
    out["episode_id"] = pd.array(episode, dtype="Int64")
    out["super"] = sup
    out["provisional"] = prov
    return out


def build_enso() -> None:
    raw = fetch(ONI_URL, "oni.ascii.txt", force=True)  # updated monthly by CPC
    out = label_phases(parse_oni(raw.read_text()))
    paths.PROCESSED.mkdir(parents=True, exist_ok=True)
    out.to_parquet(paths.PROCESSED / "enso_monthly.parquet", index=False)
    print(out.tail(6).to_string(index=False))


register("enso", build_enso, "download ONI and label ENSO phases")
