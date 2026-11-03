import subprocess

import pytest


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_require_lock_raises_without_tag(tmp_path):
    from rime.h1.run import require_prereg_lock
    _git(tmp_path, "init", "-q")
    with pytest.raises(SystemExit, match="prereg-v1"):
        require_prereg_lock(tmp_path)


def test_require_lock_returns_sha(tmp_path):
    from rime.h1.run import require_prereg_lock
    _git(tmp_path, "init", "-q")
    (tmp_path / "f").write_text("x")
    _git(tmp_path, "add", "f")
    _git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "c")
    _git(tmp_path, "tag", "prereg-v1")
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True).stdout.strip()
    assert require_prereg_lock(tmp_path) == sha


def test_h1n_family_has_nine_tests():
    from rime.h1.run import h1n_tests
    tests = h1n_tests()
    assert len(tests) == 9
    assert ("charter", "la_nina") not in tests
