"""looseball animate (3h): the frame schedule, the labels, the shading mask, the shirt numbers, and a
GIF written from synthetic data."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import synthetic as syn
import test_find_episodes as fx
from PIL import Image

from looseball import animate as ani
from looseball.adapters import Match


def _match(lead_frame=25):
    poss, tr = fx._window_fixture(lead_frame=lead_frame)
    return lambda *_args: Match(1, tr, poss, syn.PLAYERS, 10, 20, {10: "Home", 20: "Away"}, (104.0, 68.0))


def test_schedule_holds_order_and_endings():
    s = ani.schedule(start=10, anchor=14, pickup=20, ending="model", hold=0.25)
    assert [x[0] for x in s[:4]] == ["before"] * 4 and [x[1] for x in s[:4]] == [10, 11, 12, 13]
    assert s[4] == ("anchor", 14, 6)  # 1.5 s at 0.25 s a frame
    assert [x[1] for x in s if x[0] == "after"] == [15, 16, 17, 18, 19]
    assert s[-2] == ("pickup", 20, 4) and s[-1] == ("model", 14, 12)
    assert ani.schedule(5, 5, 9, ending=None)[-1] == ("pickup", 9, 4)  # no before frames, part one only
    assert ani.schedule(5, 7, 9, ending="closing")[-1] == ("closing", 9, 8)  # 2 s closing label


def test_animate_writes_a_gif_with_both_parts_and_a_sheet(tmp_path, monkeypatch):
    monkeypatch.setattr(ani, "load_match", _match())
    info = ani.animate(None, 1, 0, tmp_path / "ball.gif", sheet=tmp_path / "sheet.png")
    # release 10, anchor 25, pickup 30: 15 before, 6 at the anchor, 4 after, 4 at the pickup, 12 for the model
    assert info["enough_type"] == "move" and info["ending"] == "model"
    assert info["frames"] == 15 + 6 + 4 + 4 + 12 and info["seconds"] == pytest.approx(41 * 0.25)
    assert info["margin at the pickup point after the change"] == pytest.approx(0.0, abs=1e-9)  # level
    assert info["frames before the anchor with the drop zone in view"] == 0  # hidden until frame 25
    assert info["label clearance px"] >= ani.LABEL_GAP
    assert info["moved number clearance px"] >= ani.LABEL_GAP  # his number never sits on another dot
    with Image.open(info["file"]) as im:
        assert im.format == "GIF" and im.size == (1000, 840)
    with Image.open(tmp_path / "sheet.png") as im:
        assert im.size == (1000, 840)  # first frame, anchor, pickup, model at half size, two by two


def test_drop_zone_in_view_before_the_last_touch_and_a_short_start(tmp_path, monkeypatch):
    # the pickup point is in view from frame 15, in the first leg; the last leg starts at the contact on 20
    monkeypatch.setattr(ani, "load_match", _match(lead_frame=15))
    info = ani.animate(None, 1, 0, tmp_path / "ball.gif")
    assert (
        info["frames before the anchor"] == 10
        and info["frames before the anchor with the drop zone in view"] == 5
    )
    short = ani.animate(None, 1, 0, tmp_path / "short.gif", start_before_anchor=0.3)
    assert short["start frame"] == 17 and short["frames before the anchor"] == 3


def test_shading_is_masked_outside_the_race_circle():
    gx, gy = np.meshgrid(np.linspace(-20, 20, 41), np.linspace(-20, 20, 41))
    players = pd.DataFrame(
        {"x": [2.0, -3.0], "y": [0.0, 1.0], "vx": [0.0, 0.0], "vy": [0.0, 0.0], "team_id": [1, 2]}
    )
    mg = ani.margin_grid(players, 1, 2, gx, gy, target=(0.0, 0.0))
    inside = np.hypot(gx, gy) <= 15.0
    assert np.isfinite(mg[inside]).all() and np.isnan(mg[~inside]).all()
    # a team with nobody gets the empty-team time everywhere
    alone = ani.margin_grid(players[players["team_id"] == 2], 1, 2, gx, gy)
    assert alone[20, 20] == pytest.approx(min(2.0, 3.7 - (0.7 + np.hypot(3.0, 1.0) / 5)))


def test_shirt_numbers_fit_inside_the_dots():
    fig = plt.figure(figsize=ani.FIGSIZE, dpi=ani.DPI)
    text = fig.text(0.5, 0.5, "88", fontsize=ani.NUMBER_SIZE, fontweight="bold")
    fig.canvas.draw()
    box = text.get_window_extent()
    plt.close(fig)
    inner = (np.sqrt(ani.DOT_SIZE) - ani.DOT_EDGE) * ani.DPI / 72  # pixels inside the edge line
    assert box.width < inner and box.height < inner
    assert ani.NUMBER_SIZE * 0.5 * ani.DPI / 72 >= 8  # at half size the digits are still about 8 pixels tall


def test_the_distance_label_is_placed_clear_of_dots_and_the_marker():
    fig = plt.figure(figsize=ani.FIGSIZE, dpi=ani.DPI)
    ax = fig.add_axes([0.03, 0.17, 0.94, 0.70])
    ax.set_xlim(-20, 20)
    ax.set_ylim(-15, 15)
    ax.set_aspect("equal")
    # a crowd of dots around the midpoint, and the pickup marker on it
    obstacles = [(x, y, ani.DOT_RADIUS_PX) for x in (-2.0, 0.0, 2.0) for y in (-1.5, 0.0, 1.5)]
    obstacles.append((0.0, 0.0, ani.MARKER_RADIUS_PX))
    label = ax.text(0.0, 0.0, "13.4 m", ha="center", va="center", fontsize=12, fontweight="bold")
    clear = ani.place_label(fig, ax, label, (0.0, 0.0), obstacles)
    box = label.get_window_extent(fig.canvas.get_renderer())
    to_px = ax.transData.transform
    gaps = [ani._rect_circle_gap(box, *to_px((x, y)), r) for x, y, r in obstacles]
    plt.close(fig)
    assert clear >= ani.LABEL_GAP and min(gaps) == pytest.approx(clear)


def test_the_panel_keeps_the_whole_race_circle():
    _, tr = fx._window_fixture()
    ep = pd.Series(
        {"pickup_frame": 30, "pickup_x": 50.0, "pickup_y": 30.0}
    )  # near a corner of a 104 x 68 pitch
    xlim, ylim = ani._extent(tr, 10, ep, (104.0, 68.0))
    assert xlim[1] >= 50.0 + 15.0 and ylim[1] >= 30.0 + 15.0  # past the pitch cut at 54 and 36
    assert xlim[0] <= 50.0 - 15.0 and ylim[0] <= 30.0 - 15.0
