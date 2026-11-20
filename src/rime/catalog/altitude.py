"""Conservative extraction of the event altitude from NTSB factual narratives (precision over coverage)."""
import math
import re

NUM = r"(\d{1,2},?\d{3}|\d{3,4})"
REF = r"(?: (?P<ref>msl|agl|mean sea level|above ground level))?"
PATTERNS = [  # (regex, group index of number, scale, fixed ref or None → from group 'ref')
    (re.compile(r"\b(?:FL ?|flight level )(\d{3})\b", re.I), 1, 100, "fl"),
    (re.compile(r"\b(?:altitude|cruise|cruising|level(?:ed)? (?:off )?at)\D{0,40}?" + NUM +
                r"[ -](?:feet|ft)\b" + REF, re.I), 1, 1, None),
    (re.compile(NUM + r"[ -](?:feet|ft) (?P<ref>msl|agl|mean sea level|above ground level)\b", re.I), 1, 1, None),
]
REJECT_BEFORE = re.compile(
    r"runway|elevation|visibility|ceiling|overcast|broken|scattered|pattern altitude|traffic pattern|"
    r"filed|planned|forecast|airmet|sigmet|below|above|tops|bases|freezing level|minimum|MEA|MOCA|"
    r"density altitude|airport (?:that )?(?:was|is)|located at", re.I)
REF_NORM = {"mean sea level": "msl", "above ground level": "agl"}
REJECT_AFTER = re.compile(r"^[ -]*(?:long|wide|runway)", re.I)
VALID_FT = (100, 51_000)
SPAN_MAX = 160


def extract_altitude(text: str | None) -> tuple[float, str, str]:
    if not text:
        return math.nan, "", ""
    for rx, gi, scale, fixed_ref in PATTERNS:
        for m in rx.finditer(text):
            before = text[max(0, m.start() - 40):m.start(gi)]
            after = text[m.end(gi):m.end(gi) + 12]
            if REJECT_BEFORE.search(before) or REJECT_AFTER.search(after):
                continue
            ft = float(m.group(gi).replace(",", "")) * scale
            if not VALID_FT[0] <= ft <= VALID_FT[1]:
                continue
            raw = (m.groupdict().get("ref") or "unspecified").lower()
            ref = fixed_ref or REF_NORM.get(raw, raw)
            pad = max(0, (SPAN_MAX - (m.end() - m.start())) // 2)
            span = text[max(0, m.start() - pad):m.end() + pad][:SPAN_MAX]
            return ft, ref, span
    return math.nan, "", ""
