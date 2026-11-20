"""Conservative extraction of the event altitude from NTSB factual narratives (precision over coverage)."""
import math
import re

NUM = r"(\d{1,2},?\d{3})"
PATTERNS = [  # (regex, group index of number, scale, fixed ref or None → from group 'ref')
    (re.compile(r"\b(?:FL ?|flight level )(\d{3})\b", re.I), 1, 100, "fl"),
    (re.compile(r"\b(?:altitude|cruise|cruising|level(?:ed)? (?:off )?at)\D{0,40}?" + NUM +
                r"[ -](?:feet|ft)\b(?: (?P<ref>msl|agl))?", re.I), 1, 1, None),
    (re.compile(NUM + r"[ -](?:feet|ft) (?P<ref>msl|agl)\b", re.I), 1, 1, None),
]
REJECT_BEFORE = re.compile(r"runway|elevation|visibility|ceiling|overcast|broken|scattered", re.I)
REJECT_AFTER = re.compile(r"^[ -]*(?:long|wide|runway)", re.I)
VALID_FT = (100, 51_000)
CONTEXT = 60


def extract_altitude(text: str | None) -> tuple[float, str, str]:
    if not text:
        return math.nan, "", ""
    for rx, gi, scale, fixed_ref in PATTERNS:
        for m in rx.finditer(text):
            before = text[max(0, m.start(gi) - 30):m.start(gi)]
            after = text[m.end(gi):m.end(gi) + 12]
            if REJECT_BEFORE.search(before) or REJECT_AFTER.search(after):
                continue
            ft = float(m.group(gi).replace(",", "")) * scale
            if not VALID_FT[0] <= ft <= VALID_FT[1]:
                continue
            ref = fixed_ref or ((m.groupdict().get("ref") or "unspecified").lower())
            span = text[max(0, m.start() - CONTEXT):m.end() + CONTEXT]
            return ft, ref, span
    return math.nan, "", ""
