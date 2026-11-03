"""Cached downloads with a checksum manifest at data/raw/MANIFEST.json."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

from rime import paths

USER_AGENT = "rime-research/0.1 (public aviation-weather study)"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _manifest_path() -> Path:
    return paths.RAW / "MANIFEST.json"


def _load_manifest() -> dict:
    p = _manifest_path()
    return json.loads(p.read_text()) if p.exists() else {}


def fetch(url: str, name: str, *, force: bool = False) -> Path:
    """Download url to RAW/name unless a verified cached copy exists."""
    paths.RAW.mkdir(parents=True, exist_ok=True)
    dest = paths.RAW / name
    manifest = _load_manifest()
    entry = manifest.get(name)
    if not force and dest.exists() and entry and entry.get("sha256") == _sha256(dest):
        _check_pinned(name, entry["sha256"])
        return dest

    part = dest.with_name(dest.name + ".part")
    with requests.get(url, stream=True, timeout=120, headers={"User-Agent": USER_AGENT}) as r:
        r.raise_for_status()
        with part.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    part.replace(dest)

    manifest[name] = {
        "url": url,
        "sha256": _sha256(dest),
        "bytes": dest.stat().st_size,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    _manifest_path().write_text(json.dumps(manifest, indent=2, sort_keys=True))
    _check_pinned(name, manifest[name]["sha256"])
    return dest


def _check_pinned(name: str, sha256: str) -> None:
    """Warn when a file differs from the version pinned in data/manual/data_versions.json.

    NTSB re-publishes its database monthly and keeps no archive, so a fresh clone can
    only get the current file; the warning makes the difference visible.
    """
    pinned_path = paths.MANUAL / "data_versions.json"
    if not pinned_path.exists():
        return
    pinned = json.loads(pinned_path.read_text()).get(name)
    if pinned and pinned.get("sha256") != sha256:
        print(f"WARNING: {name} differs from the pinned version "
              f"(retrieved {pinned.get('retrieved_at_utc', '?')}); results may not match the published ones.")
