"""3h output: clips_enough.csv beside an unchanged clips.csv, and the reproduce checker."""

import importlib.util
import shutil
from pathlib import Path

import pandas as pd
import test_cli

from looseball import cli, export_clips
from looseball.export_clips import COLUMNS, ENOUGH_FILE_COLUMNS, export_clips_enough

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ["match_id", "seq_i", "period", "clock", "frame", "team", "verdict", "deficit_s", "metres_short",
            "enough_type", "enough_player", "enough_metres", "enough_degrees", "enough_player_gk",
            "enough_player_extrapolated"]  # fmt: skip


def _inputs():
    decomposed = pd.DataFrame({"match_id": [2, 1, 1], "seq_i": [5, 9, 3], "losing_team": [10, 20, 10],
                               "verdict": ["reading", "positioning", "after the anchor"]})  # fmt: skip
    episodes = pd.DataFrame(
        {"match_id": [1, 1, 2], "seq_i": [3, 9, 5], "period_id": [1, 2, 1], "anchor_frame": [30, 900, 50]}
    )
    clocks = {1: pd.Series({30: "00:00:02.00", 900: "00:46:29.00"}), 2: pd.Series({50: "00:00:04.00"})}
    table = pd.DataFrame({"match_id": [1, 1, 2], "seq_i": [3, 9, 5], "deficit_s": [-0.2, 0.31234, 0.1],
                          "metres_short": [None, 1.5617, 0.5], "enough_type": [None, "move", "redirect"],
                          "enough_player": [None, "away_2", "home_1"], "enough_metres": [None, 1.5617, None],
                          "enough_degrees": [None, None, 12.5], "enough_player_gk": [None, False, True],
                          "enough_player_extrapolated": [None, True, False]})  # fmt: skip
    for c in ("enough_player_gk", "enough_player_extrapolated"):
        table[c] = table[c].astype("boolean")
    return decomposed, episodes, clocks, table


def test_clips_enough_columns_rows_and_order_match_clips(tmp_path):
    decomposed, episodes, clocks, table = _inputs()
    clips = export_clips(decomposed, episodes, clocks, path=tmp_path / "clips.csv")
    before = (tmp_path / "clips.csv").read_bytes()
    out = export_clips_enough(decomposed, episodes, clocks, table, path=tmp_path / "clips_enough.csv")
    assert ENOUGH_FILE_COLUMNS == EXPECTED and list(out.columns) == EXPECTED
    assert out[COLUMNS].equals(clips)  # same rows, same order, same six values
    assert (tmp_path / "clips.csv").read_bytes() == before
    written = (tmp_path / "clips_enough.csv").read_text().splitlines()
    assert written[0] == ",".join(EXPECTED)
    assert written[1] == "1,3,1,00:00:02.00,30,10,after the anchor,-0.2000,,,,,,,"
    assert written[2].endswith(",0.3123,1.5617,move,away_2,1.5617,,False,True")


def test_run_writes_clips_enough_and_leaves_clips_as_before(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "load_match", test_cli._synthetic_match)
    assert cli.main(["run", "--data", str(tmp_path), "--match", "1", "--out", str(tmp_path / "out")]) == 0
    clips = pd.read_csv(tmp_path / "out" / "clips.csv")
    enough = pd.read_csv(tmp_path / "out" / "clips_enough.csv")
    assert list(clips.columns) == COLUMNS and list(enough.columns) == EXPECTED
    assert enough[COLUMNS].equals(clips)


def test_check_reproduce_ignores_the_new_file(tmp_path):
    """The checker compares the six MT1 files, report.md and static_temperature.md; an extra
    clips_enough.csv in the output does not change its verdict."""
    spec = importlib.util.spec_from_file_location("check_reproduce", ROOT / "scripts" / "check_reproduce.py")
    check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(check)
    for f in (ROOT / "audit" / "mt1_test").iterdir():
        shutil.copy(f, tmp_path / f.name)
    audit = (ROOT / "AUDIT.md").read_text()
    start = audit.index("MT1 on the test matches (15):")
    (tmp_path / "report.md").write_text(audit[start : audit.index("\nGate verdicts.\n", start)])
    shutil.copy(ROOT / "audit" / "static_temperature_test.md", tmp_path / "static_temperature.md")
    (tmp_path / "clips_enough.csv").write_text(",".join(EXPECTED) + "\n")
    assert check.main(tmp_path) == 0
    (tmp_path / "clips.csv").write_text("changed\n")
    assert check.main(tmp_path) == 1
