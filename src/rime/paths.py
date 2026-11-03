"""Project paths. RIME_DATA_DIR overrides the data/ root (used by tests)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ.get("RIME_DATA_DIR", ROOT / "data"))
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
MANUAL = ROOT / "data" / "manual"
RESULTS = DATA.parent / "results"
