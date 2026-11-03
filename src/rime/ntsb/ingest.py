"""Download the NTSB aviation accident databases and convert tables to Parquet."""
import zipfile
from pathlib import Path

import pandas as pd
from access_parser import AccessParser

from rime import paths
from rime.cli import register
from rime.download import fetch

SOURCES = {
    "avall": "https://data.ntsb.gov/avdata/FileDirectory/DownloadFile?fileID=avall.zip",
    "pre2008": "https://data.ntsb.gov/avdata/FileDirectory/DownloadFile?fileID=Pre2008.zip",
}
TABLES = ["events", "aircraft", "engines", "Findings", "Events_Sequence",
          "Occurrences", "seq_of_events", "narratives"]


def read_mdb_table(mdb: Path, table: str, db: AccessParser | None = None) -> pd.DataFrame:
    db = db or AccessParser(str(mdb))
    data = db.parse_table(table)
    return pd.DataFrame({k: list(v) for k, v in data.items()})


def combine(avall: pd.DataFrame, pre2008: pd.DataFrame, key: str = "ev_id") -> pd.DataFrame:
    """Stack both databases; where an ev_id is in both, keep only the avall rows."""
    a = avall.assign(source_db="avall")
    p = pre2008[~pre2008[key].isin(set(avall[key]))].assign(source_db="pre2008")
    frames = [f for f in (a, p) if len(f)]
    if not frames:
        return a
    return pd.concat(frames, ignore_index=True)


def _unzip_mdb(zip_path: Path, name: str) -> Path:
    out = paths.RAW / f"{name}.mdb"
    if out.exists() and out.stat().st_mtime >= zip_path.stat().st_mtime:
        return out
    with zipfile.ZipFile(zip_path) as z:
        member = next(m for m in z.namelist() if m.lower().endswith(".mdb"))
        with z.open(member) as src, out.open("wb") as dst:
            while chunk := src.read(1 << 20):
                dst.write(chunk)
    return out


def _arrow_safe(df: pd.DataFrame) -> pd.DataFrame:
    """Columns mixing types (e.g. int and str) become strings; None stays null."""
    for col in df.columns:
        if df[col].dtype == object:
            kinds = {type(v) for v in df[col].dropna()}
            if len(kinds) > 1:
                df[col] = df[col].map(lambda v: None if v is None else str(v))
    return df


def ingest() -> None:
    out_dir = paths.INTERIM / "ntsb"
    out_dir.mkdir(parents=True, exist_ok=True)
    dbs = {}
    for name, url in SOURCES.items():
        mdb = _unzip_mdb(fetch(url, f"{name}.zip"), name)
        dbs[name] = AccessParser(str(mdb))
    for table in TABLES:
        frames = {name: read_mdb_table(Path(), table, db) for name, db in dbs.items()}
        df = _arrow_safe(combine(frames["avall"], frames["pre2008"]))
        df.to_parquet(out_dir / f"{table}.parquet", index=False)
        by_src = df["source_db"].value_counts().to_dict() if len(df) else {}
        print(f"  {table}: {len(df):,} rows {by_src}")


register("ntsb", ingest, "download NTSB databases and convert to Parquet")
