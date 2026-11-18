"""Path check (report-only), synthetic data."""

import numpy as np
import pandas as pd
import pytest
import synthetic as syn

from looseball.pathcheck import favourite, is_ground, path_check
from looseball.velocities import tracking_velocities

N = 40


def _match(ball, players, z=None):
    tr = syn.tracking(N, ball, players)
    if z is not None:
        tr["ball_z"] = z
    return tr


def _ball(release=10, anchor=15, pickup=35, losing=10, winning=20):
    x = -20 + 20 * pickup / (N - 1)  # the ball on the pickup frame in these fixtures
    return pd.DataFrame([{"match_id": 1, "seq_i": 0, "release_frame": release, "anchor_frame": anchor,
                          "pickup_frame": pickup, "pickup_x": x, "pickup_y": 0.0, "losing_team": losing,
                          "winning_team": winning}])  # fmt: skip


def test_favourite_rule():
    assert favourite(None, None, "a", "b") == "unreached"
    assert favourite(20, None, "a", "b") == "a" and favourite(None, 20, "a", "b") == "b"
    assert favourite(20, 25, "a", "b") == "a" and favourite(25, 20, "a", "b") == "b"
    assert favourite(20, 20, "a", "b") == "tie"


def test_the_loser_reaches_the_path_first_though_the_winner_is_at_the_pickup():
    # ball rolls from (-20, 0) towards (0, 0); the loser (team 10) stands ahead of it on the path, the winner
    # (team 20) stands at the pickup point
    ball = np.column_stack([np.linspace(-20, 0, N), np.zeros(N)])
    players = {"home_1": syn.still(N, -8.0, 1.0), "away_2": syn.still(N, 0.5, 0.0)}
    tr = _match(ball, players)
    out = path_check(_ball(), tr, tracking_velocities(tr), syn.PLAYERS).iloc[0]
    assert out["ground"] and out["path_frames"] == 21
    assert out["static 0.3 favourite"] == "loser" and out["dynamic 0.3 favourite"] == "loser"
    assert out["static 0.3 first loser"] < out["static 0.3 first winner"]
    # with tolerance 0 the first reachable frames are later
    assert out["static 0 first loser"] >= out["static 0.3 first loser"]
    # P1b: at the pickup point (-2.05, 0), from all players, the winner standing 2.55 m away is favourite
    assert out["pickup favourite all players"] == "winner"
    assert out["pickup best winner"] == pytest.approx(0.7 + np.hypot(0.5 + 20 - 20 * 35 / 39, 0.0) / 5)
    # ball path from release (frame 10) to pickup (frame 35): 25 steps of 20/39 m
    assert out["ball_path_m"] == pytest.approx(25 * 20 / 39)


def test_unreached_tie_aerial_and_undetected_frames():
    ball = np.column_stack([np.linspace(-20, 0, N), np.zeros(N)])
    far = {"home_1": syn.still(N, 0.0, 30.0), "away_2": syn.still(N, 0.0, -30.0)}
    tr = _match(ball, far)
    assert (
        path_check(_ball(), tr, tracking_velocities(tr), syn.PLAYERS).iloc[0]["static 0.3 favourite"]
        == "unreached"
    )

    mirror = {"home_1": syn.still(N, -5.0, 3.0), "away_2": syn.still(N, -5.0, -3.0)}
    tr = _match(ball, mirror)
    assert (
        path_check(_ball(), tr, tracking_velocities(tr), syn.PLAYERS).iloc[0]["static 0.3 favourite"] == "tie"
    )

    z = np.zeros(N)
    z[20] = 2.5  # above 1.8 m inside the window with the ball detected: aerial
    tr = _match(ball, mirror, z)
    assert not is_ground(tr, 10, 35)
    out = path_check(_ball(), tr, tracking_velocities(tr), syn.PLAYERS).iloc[0]
    assert not out["ground"] and pd.isna(out["dynamic 0.3 favourite"])
    tr["ball_detected"] = pd.array([False] * N, dtype="boolean")
    assert is_ground(tr, 10, 35)  # undetected frames cannot make a ball aerial
    tr = _match(ball, mirror)
    tr.loc[15:30, "ball_detected"] = False
    assert path_check(_ball(), tr, tracking_velocities(tr), syn.PLAYERS).iloc[0]["path_frames"] == 5
