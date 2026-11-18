"""looseball animate (3h): the frame schedule and a GIF written from synthetic data."""

import pytest
import test_cli
from PIL import Image

from looseball import animate as ani


def test_schedule_holds_and_order():
    s = ani.schedule(release=10, anchor=14, pickup=20, model_part=True, hold=0.25)
    assert [x[0] for x in s[:4]] == ["before"] * 4 and [x[1] for x in s[:4]] == [10, 11, 12, 13]
    assert s[4] == ("anchor", 14, 6)  # 1.5 s at 0.25 s a frame
    assert [x[1] for x in s if x[0] == "after"] == [15, 16, 17, 18, 19]
    assert s[-2] == ("pickup", 20, 4) and s[-1] == ("model", 14, 12)
    assert ani.schedule(5, 5, 9, model_part=False)[-1] == ("pickup", 9, 4)  # no before frames, no part two


def test_animate_writes_a_gif_with_both_parts(tmp_path, monkeypatch):
    monkeypatch.setattr(ani, "load_match", test_cli._synthetic_match)
    info = ani.animate(None, 1, 0, tmp_path / "ball.gif")
    # release 10, anchor 25, pickup 30: 15 before, 6 at the anchor, 4 after, 4 at the pickup, 12 for the model
    assert info["enough_type"] == "move" and info["model part"]
    assert info["frames"] == 15 + 6 + 4 + 4 + 12 and info["seconds"] == pytest.approx(41 * 0.25)
    assert info["margin at the pickup point after the change"] == pytest.approx(0.0, abs=1e-9)  # level
    with Image.open(info["file"]) as im:
        assert im.format == "GIF" and im.size == (1000, 840)


def test_a_ball_outside_the_analysis_set_is_refused(monkeypatch):
    monkeypatch.setattr(ani, "load_match", test_cli._synthetic_match)
    with pytest.raises(ValueError, match="not a lost ball of the analysis set"):
        ani.episode(None, 1, 99)
