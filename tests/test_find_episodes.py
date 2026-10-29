import numpy as np
import pandas as pd
import pytest
import synthetic as syn

from looseball import find_episodes
from looseball.episodes import possession_pairs

P = syn.possession


def _pair_fixture():
    rows = [
        P(0, 5, 10, 1, "unknown", "pass", "fail"),  # 0 -> 1: T2, candidate
        P(10, 14, 20, 2, "recovery", "pass", "success"),  # 1 -> 2: T0, reference only
        P(18, 20, 20, 2, "reception", "clearance"),  # 2 -> 3: next is a restart, dropped
        P(30, 32, 10, 1, "restart", "loss"),  # 3 -> 4: T4, gap exactly 3, candidate
        P(35, 38, 10, 3, "kept", "pass", "success"),  # 4 -> 5: T7, candidate
        P(42, 45, 20, 2, "recovery", "shot"),  # 5 -> 6: held save by a goalkeeper, excluded
        P(49, 50, 20, 4, "recovery", "clearance", header=True, goalkeeper=True),  # 6 -> 7: T5 before T1
        P(54, 55, 10, 1, "recovery", "pass", "offside"),  # 7 -> 8: offside, dropped
        P(60, 61, 20, 2, "recovery", "foul"),  # 8 -> 9: foul, dropped
        P(65, 66, 10, 1, "recovery", "loss", after=True),  # 9 -> 10: stoppage, dropped
        P(70, 71, 20, 2, "recovery", "unknown"),  # 10 -> 11: same player, excluded
        P(75, 76, 20, 2, "recovery", "loss"),  # 11 -> 12: gap 2, excluded
        P(78, 79, 10, 1, "recovery", "loss"),  # 12 -> 13: period boundary, dropped
        P(90, 91, 20, 2, "recovery", "pass", "success", period=2),
    ]
    return syn.possessions(rows)


def test_pair_rules_triggers_and_exclusions():
    pairs = possession_pairs(_pair_fixture())
    assert list(pairs["trigger"][:8]) == ["T2", "T0", "T1", "T4", "T7", "T3", "T5", "other"]
    assert list(pairs.loc[pairs["candidate"], "seq_i"]) == [0, 3, 4, 6]
    assert not pairs.loc[[2, 7, 8, 9, 12], "retained"].any()
    assert pairs.loc[3, "gap"] == 3 and pairs.loc[11, "gap"] == 2


def test_find_episodes_on_the_pair_fixture():
    n = 100
    ball = np.zeros((n, 2))
    players = {"home_1": syn.still(n, 2, 0), "away_2": syn.still(n, -2, 0), "home_3": syn.still(n, 0, 3),
               "away_4": syn.still(n, 0, -3)}  # fmt: skip
    ep = find_episodes(_pair_fixture(), syn.tracking(n, ball, players), syn.PLAYERS)
    assert list(ep["seq_i"]) == [0, 3, 4, 6]
    assert list(ep["trigger"]) == ["T2", "T4", "T7", "T5"]
    assert (ep["anchor_frame"] == ep["release_frame"]).all()  # pickup point always in view
    assert ep["kept"].all() and (ep["n_in_radius"] == 4).all()


def _window_fixture(lead_frame=25, hidden_player_detected=True):
    n = 40
    ball = np.zeros((n, 2))
    ball[10:21, 0] = np.arange(0, 11)  # +x at 10 m/s from release (frame 10) to frame 20
    ball[21:, 0] = 10
    ball[21:, 1] = np.arange(1, n - 20)  # then +y: a 90 degree turn at frame 20
    ball[:10] = ball[10]
    view_left = [(-60.0, 40.0), (5.0, 40.0), (5.0, -40.0), (-60.0, -40.0)]  # pickup point (10, 10) hidden
    views = [view_left if f < lead_frame else syn.FULL_VIEW for f in range(n)]
    players = {
        "home_1": syn.still(n, 10, 1),  # beside the ball at the turn
        "away_2": syn.still(n, 10, 12),
        "home_3": syn.still(n, 4, 4, detected=hidden_player_detected),
        "away_4": syn.still(n, 40, 0),  # beyond 15 m
    }
    poss = syn.possessions(
        [P(0, 10, 10, 1, "unknown", "pass", "fail"), P(30, 35, 20, 2, "recovery", "pass", "success")]
    )
    return poss, syn.tracking(n, ball, players, views)


def test_contact_legs_anchors_lead_and_gate():
    poss, tr = _window_fixture()
    ep = find_episodes(poss, tr, syn.PLAYERS).iloc[0]
    assert ep["contact_frames"] == "20" and ep["n_legs"] == 2
    assert (ep["leg1_start"], ep["leg1_end"], ep["leg2_start"], ep["leg2_end"]) == (10, 20, 20, 30)
    assert pd.isna(ep["anchor1_frame"]) and ep["anchor_frame"] == 25  # first leg never sees the drop zone
    assert ep["lead_s"] == pytest.approx(0.5) and not ep["immediate"]
    assert (ep["pickup_x"], ep["pickup_y"]) == (10.0, 10.0)
    assert ep["n_in_radius"] == 3 and ep["kept"]


def test_gate_and_immediate_flags():
    poss, tr = _window_fixture(lead_frame=27, hidden_player_detected=False)
    ep = find_episodes(poss, tr, syn.PLAYERS).iloc[0]
    assert ep["lead_s"] == pytest.approx(0.3) and ep["immediate"]
    assert ep["n_detected_in_radius"] == 2 and not ep["kept"]  # 2 of 3 detected is under 85%
