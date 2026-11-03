import hashlib
import http.server
import json
import threading

import pytest


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("RIME_DATA_DIR", str(tmp_path / "data"))
    import importlib
    import rime.paths
    import rime.download
    importlib.reload(rime.paths)
    importlib.reload(rime.download)
    yield tmp_path / "data"
    monkeypatch.delenv("RIME_DATA_DIR")
    importlib.reload(rime.paths)  # don't leak tmp paths into later tests
    importlib.reload(rime.download)


@pytest.fixture
def server(tmp_path):
    payload = b"x" * 1024
    hits = {"n": 0}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            hits["n"] += 1
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_port}/file.bin", payload, hits
    srv.shutdown()


def test_fetch_downloads_and_records_manifest(data_dir, server):
    from rime.download import fetch
    url, payload, _ = server
    path = fetch(url, "file.bin")
    assert path.read_bytes() == payload
    manifest = json.loads((data_dir / "raw" / "MANIFEST.json").read_text())
    entry = manifest["file.bin"]
    assert entry["url"] == url
    assert entry["sha256"] == hashlib.sha256(payload).hexdigest()
    assert entry["bytes"] == 1024
    assert "retrieved_at_utc" in entry


def test_fetch_skips_when_cached(data_dir, server):
    from rime.download import fetch
    url, _, hits = server
    fetch(url, "file.bin")
    fetch(url, "file.bin")
    assert hits["n"] == 1


def test_fetch_redownloads_on_checksum_mismatch(data_dir, server):
    from rime.download import fetch
    url, payload, hits = server
    path = fetch(url, "file.bin")
    path.write_bytes(b"corrupt")
    path = fetch(url, "file.bin")
    assert hits["n"] == 2
    assert path.read_bytes() == payload


def test_fetch_warns_when_pinned_checksum_differs(data_dir, server, tmp_path, monkeypatch, capsys):
    from rime import paths
    from rime.download import fetch
    url, _, _ = server
    manual = tmp_path / "manual"
    manual.mkdir()
    (manual / "data_versions.json").write_text(json.dumps({"file.bin": {"sha256": "0" * 64}}))
    monkeypatch.setattr(paths, "MANUAL", manual)
    fetch(url, "file.bin")
    assert "differs from the pinned version" in capsys.readouterr().out
