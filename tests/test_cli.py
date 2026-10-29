import ast
from pathlib import Path

import pandas as pd
import pytest
import synthetic as syn
import test_find_episodes as fx

from looseball import cli
from looseball.adapters import Match

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "looseball"


def _synthetic_match(*_args) -> Match:
    poss, tr = fx._window_fixture()
    return Match(1, tr, poss, syn.PLAYERS, 10, 20, {10: "Home", 20: "Away"}, (104.0, 68.0))


def test_run_writes_the_team_report_and_clips(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "load_match", _synthetic_match)
    assert cli.main(["run", "--data", str(tmp_path), "--match", "1", "--out", str(tmp_path / "out")]) == 0
    clips = pd.read_csv(tmp_path / "out" / "clips.csv")
    assert list(clips.columns) == ["match_id", "period", "clock", "frame", "team", "verdict"]
    assert len(clips) == 1 and clips.loc[0, "frame"] == 25 and clips.loc[0, "team"] == 10
    verdicts = pd.read_csv(tmp_path / "out" / "team_verdicts.csv")
    assert list(verdicts["name"]) == ["Home"] and verdicts.loc[0, "lost"] == 1


def test_commands_and_arguments():
    with pytest.raises(SystemExit):
        cli.main([])
    with pytest.raises(SystemExit):
        cli.main(["reproduce", "--data", "x"])  # --out is required


def test_the_reproduction_path_never_refits():
    for name in ("reproduce.py", "cli.py"):
        tree = ast.parse((PACKAGE / name).read_text())
        called = {n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
                  for n in ast.walk(tree) if isinstance(n, ast.Call)}  # fmt: skip
        imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
        assert not ({"refit", "fit"} & (called | imported)), name
