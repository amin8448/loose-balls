"""3h, what would have been enough (DESIGN.md "3h. What would have been enough"), synthetic data."""

import numpy as np
import pandas as pd
import pytest

from looseball.enough import (
    COLUMNS,
    displacement_bisection,
    enough,
    enough_one,
    rotation_bisection,
    rotation_closed_form,
)
from looseball.race import ReachModel

TARGET = np.array([0.0, 0.0])


def _race(players, empty_sides=()):
    """players: (column_id, side, x, y, vx, vy[, detected, goalkeeper]) with the frozen model's times."""
    model = ReachModel()
    rows = []
    for p in players:
        cid, side, x, y, vx, vy = p[:6]
        detected = p[6] if len(p) > 6 else True
        gk = p[7] if len(p) > 7 else False
        vel = np.nan_to_num(np.array([vx, vy], float))
        rows.append({"match_id": 1, "seq_i": 0, "column_id": cid, "side": side, "x": x, "y": y, "vx": vx, "vy": vy,
                     "velocity_missing": bool(np.isnan(vx)), "detected": detected, "goalkeeper": gk,
                     "dist": float(np.hypot(x, y)), "t_static": model.tti(np.array([x, y]), TARGET, np.zeros(2)),
                     "t_dynamic": model.tti(np.array([x, y]), TARGET, vel), "empty_team": False})  # fmt: skip
    for side in empty_sides:
        rows.append({"match_id": 1, "seq_i": 0, "side": side, "dist": 15.0, "t_static": 3.7, "t_dynamic": 3.7,
                     "empty_team": True, "velocity_missing": False})  # fmt: skip
    return pd.DataFrame(rows)


def test_moving_the_best_placed_player_by_metres_short_gives_t_w():
    # winner standing 6 m away; loser 10 m away moving sideways at 3 m/s (cannot be redirected enough)
    race = _race([("away_2", "other", 6.0, 0.0, 0.0, 0.0), ("home_1", "releasing", 0.0, 10.0, 3.0, 0.0)])
    e = enough_one(race, "releasing", "positioning", TARGET)
    t_w = 0.7 + 6 / 5
    model = ReachModel()
    pos, vel = np.array([0.0, 10.0]), np.array([3.0, 0.0])
    drift = TARGET - (pos + 0.7 * vel)
    moved = pos + e["metres_short"] * drift / np.hypot(*drift)
    assert e["deficit_s"] == pytest.approx(model.tti(pos, TARGET, vel) - t_w)
    assert e["metres_short"] == pytest.approx(5 * e["deficit_s"])
    assert model.tti(moved, TARGET, vel) == pytest.approx(t_w, abs=1e-9)


def _brute_rotation(d, speed, t_w, phi, model, n=400_001):
    """Smallest rotation from the current angle phi that flips, by scanning every velocity angle a
    (measured from the direction to the pickup point; the model is symmetric in its sign)."""
    pos = np.array([d, 0.0])  # the pickup point is at the origin, the direction to it is (-1, 0)
    a = np.linspace(0.0, np.pi, n)
    feasible = [model.tti(pos, TARGET, speed * np.array([-np.cos(x), np.sin(x)])) <= t_w for x in a]
    return float(np.min(np.abs(phi - a[np.array(feasible)])))


@pytest.mark.parametrize(
    "d, speed, t_w, phi",
    [
        (8.0, 4.0, 1.9, 2.0),  # ordinary case
        (2.0, 5.0, 1.1, 1.5),  # overshoot: the 3.5 m drift is longer than the 2 m distance
        (10.0, 2.0, 2.5, np.pi),  # running directly away
    ],
)
def test_rotation_formula_against_a_brute_force_scan(d, speed, t_w, phi):
    model = ReachModel()
    closed = rotation_closed_form(d, 0.7 * speed, 5 * (t_w - 0.7), phi)
    brute = _brute_rotation(d, speed, t_w, phi, model)
    assert np.isfinite(closed)
    assert closed == pytest.approx(brute, abs=1e-4)
    # the closed form and the bisection agree under the frozen model
    pos = np.array([d, 0.0])
    vel = speed * np.array([-np.cos(phi), np.sin(phi)])
    assert rotation_bisection(model, pos, vel, TARGET, t_w) == pytest.approx(closed, abs=1e-6)


def test_overshoot_case_where_no_rotation_flips():
    # 0.7 x 8 = 5.6 m of drift on a player 1 m away: the drifted position is at least 4.6 m away
    assert np.isnan(rotation_closed_form(1.0, 5.6, 5 * (1.2 - 0.7), 1.0))


def test_pleuler_bisections_reach_t_w():
    model = ReachModel("pleuler")
    pos, vel = np.array([0.0, 10.0]), np.array([3.0, 0.0])
    t_w = 1.9
    delta = displacement_bisection(model, pos, vel, TARGET, t_w)
    drift = TARGET - (pos + 0.7 * vel)
    assert model.tti(pos + delta * drift / np.hypot(*drift), TARGET, vel) == pytest.approx(t_w, abs=1e-6)
    rot = rotation_bisection(model, np.array([8.0, 0.0]), np.array([0.0, 4.0]), TARGET, 2.6)
    assert np.isfinite(rot) and 0 < rot < np.pi / 2
    # after that rotation the pleuler time equals t_w
    u = np.array([-1.0, 0.0])
    a = np.pi / 2 - rot  # remaining angle from the direction to the pickup point, on the velocity's side
    v = 4.0 * np.array([np.cos(a) * u[0] - np.sin(-a) * u[1], np.sin(-a) * u[0] + np.cos(a) * u[1]])
    assert model.tti(np.array([8.0, 0.0]), TARGET, v) == pytest.approx(2.6, abs=1e-6)


def test_redirect_is_preferred_and_the_smallest_rotation_wins():
    race = _race(
        [
            ("away_2", "other", 7.0, 0.0, 0.0, 0.0),  # t_w = 2.1
            ("home_1", "releasing", 0.0, 8.0, 4.0, 0.0),  # sideways, 90 degrees off
            (
                "home_3",
                "releasing",
                -8.0,
                0.0,
                0.0,
                -4.0,
                False,
                True,
            ),  # sideways too, extrapolated goalkeeper
            ("home_5", "releasing", 0.0, -9.0, 0.0, -4.0),  # running away, 180 degrees off
        ]
    )
    e = enough_one(race, "releasing", "reading", TARGET)
    assert e["enough_type"] == "redirect"
    # home_1 and home_3 need the same rotation (within 1e-9); home_1 is nearer (8 m both) -> column_id
    assert e["enough_player"] == "home_1"
    assert e["enough_degrees"] > 0 and e["enough_metres"] is None
    assert e["enough_player_gk"] is False and e["enough_player_extrapolated"] is False


def test_ties_for_the_best_placed_player_break_on_distance_then_column_id():
    # two losing players standing (no velocity: no redirection) with equal reach times
    race = _race(
        [
            ("away_2", "other", 4.0, 0.0, 0.0, 0.0),
            ("home_7", "releasing", 0.0, 9.0, 0.0, 0.0),
            ("home_3", "releasing", 9.0, 0.0, 0.0, 0.0, False, True),
            ("home_9", "releasing", 0.0, -9.0, np.nan, np.nan),
        ]
    )
    e = enough_one(race, "releasing", "positioning", TARGET)
    assert e["enough_type"] == "move" and e["enough_player"] == "home_3"  # same 9 m: column_id decides
    assert e["enough_player_gk"] is True and e["enough_player_extrapolated"] is True
    assert e["enough_metres"] == pytest.approx(5.0)  # 5 x (2.5 - 1.5)
    # a nearer player with a time within 1e-9 s wins on distance
    race.loc[race["column_id"] == "home_7", "dist"] = 8.999
    assert enough_one(race, "releasing", "positioning", TARGET)["enough_player"] == "home_7"


def test_empty_losing_side_negative_deficit_and_after_the_anchor():
    race = _race([("away_2", "other", 12.0, 0.0, 0.0, 0.0)], empty_sides=("releasing",))
    e = enough_one(race, "releasing", "positioning", TARGET)
    assert e["enough_type"] == "no_player_in_race" and e["enough_player"] is None
    assert e["deficit_s"] == pytest.approx(3.7 - 3.1) and e["metres_short"] == pytest.approx(3.0)

    race = _race([("away_2", "other", 9.0, 0.0, 0.0, 0.0), ("home_1", "releasing", 0.0, 10.0, 0.0, -4.0)])
    e = enough_one(race, "releasing", "positioning", TARGET)  # moving straight at it: dynamic favourite
    assert e["deficit_s"] < 0 and e["enough_type"] == "already_favourite" and e["metres_short"] is None

    e = enough_one(race, "releasing", "after the anchor", TARGET)
    assert e["enough_type"] is None and e["deficit_s"] < 0
    assert all(e[c] is None for c in COLUMNS if c != "deficit_s")


def test_enough_table_shape_and_types():
    race = _race([("away_2", "other", 6.0, 0.0, 0.0, 0.0), ("home_1", "releasing", 0.0, 10.0, 3.0, 0.0)])
    balls = pd.DataFrame([{"match_id": 1, "seq_i": 0, "loser_side": "releasing", "verdict": "positioning",
                           "pickup_x": 0.0, "pickup_y": 0.0}])  # fmt: skip
    t = enough(race, balls)
    assert list(t.columns) == ["match_id", "seq_i", *COLUMNS]
    assert str(t["enough_player_gk"].dtype) == "boolean" and t.loc[0, "enough_type"] in ("redirect", "move")
