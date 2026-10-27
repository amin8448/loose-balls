import builtins
import subprocess

import pytest

from looseball import guard, io, paths

TEST_ID = 1874553
EXPLORATION_ID = 1886347


def test_test_match_raises_before_any_file_is_opened(monkeypatch):
    opened = []
    real_open = builtins.open

    def recording_open(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", recording_open)
    with pytest.raises(guard.TestSetLocked):
        io.load_metadata(TEST_ID)
    assert not any(str(TEST_ID) in p for p in opened)


def test_exploration_match_loads():
    meta = io.load_metadata(EXPLORATION_ID)
    assert int(meta["id"]) == EXPLORATION_ID


def test_every_test_match_is_refused_and_unknown_ids_too():
    for match_id in paths.TEST:
        with pytest.raises(guard.TestSetLocked):
            guard.match_path(match_id, "tracking")
        with pytest.raises(guard.TestSetLocked):
            guard.cache_path(match_id, "frames")
    with pytest.raises(guard.UnknownMatch):
        guard.check(1)


def test_marker_counts_only_once_committed(tmp_path):
    def git(*args):
        subprocess.run(
            ["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@t", *args],
            check=True,
            capture_output=True,
        )

    git("init", "-q")
    audit = tmp_path / "AUDIT.md"
    audit.write_text("# Audit log\n")
    git("add", "AUDIT.md")
    git("commit", "-q", "-m", "audit")
    with pytest.raises(guard.TestSetLocked):
        guard.check(TEST_ID, root=tmp_path)

    audit.write_text("# Audit log\nMAIN-TEST-PLAN: plan v1\n")
    with pytest.raises(guard.TestSetLocked):
        guard.check(TEST_ID, root=tmp_path)

    git("commit", "-q", "-am", "plan")
    assert guard.check(TEST_ID, root=tmp_path) == TEST_ID
