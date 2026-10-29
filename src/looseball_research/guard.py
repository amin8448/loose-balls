"""The test-set rule.

Exploration matches load freely. A test match loads only when the committed AUDIT.md
(the version at git HEAD, not the working copy) contains a main-test plan marker: a line
that starts with "MAIN-TEST-PLAN: " followed by a reference to the plan. Any other match
id is refused.

Every path to the files of a single match, raw or cached, is issued by match_path or
cache_path below, so the check runs before any file of that match is opened.
"""

import re
import subprocess
from pathlib import Path

from looseball_research import paths

MARKER = re.compile(r"^MAIN-TEST-PLAN: \S", re.MULTILINE)


class TestSetLocked(RuntimeError):
    """Raised when a test match is requested without a committed main-test plan."""

    __test__ = False


class UnknownMatch(ValueError):
    """Raised for a match id in neither set."""


def committed_audit(root: Path = paths.ROOT) -> str:
    """AUDIT.md as committed at HEAD, or an empty string if there is none."""
    result = subprocess.run(
        ["git", "-C", str(root), "show", "HEAD:AUDIT.md"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout if result.returncode == 0 else ""


def main_test_unlocked(root: Path = paths.ROOT) -> bool:
    return MARKER.search(committed_audit(root)) is not None


def check(match_id: int, root: Path = paths.ROOT) -> int:
    """Return the match id as int if it may be loaded, raise otherwise."""
    match_id = int(match_id)
    if match_id in paths.EXPLORATION:
        return match_id
    if match_id in paths.TEST:
        if main_test_unlocked(root):
            return match_id
        raise TestSetLocked(
            f"match {match_id} is a test match; no main-test plan marker in the committed AUDIT.md"
        )
    raise UnknownMatch(f"match {match_id} is in neither the exploration nor the test set")


def match_path(match_id: int, kind: str) -> Path:
    match_id = check(match_id)
    return paths.MATCHES_DIR / str(match_id) / f"{match_id}{paths.RAW_SUFFIX[kind]}"


def cache_path(match_id: int, name: str) -> Path:
    match_id = check(match_id)
    return paths.CACHE / f"{match_id}_{name}.parquet"
