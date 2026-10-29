import numpy as np
import pandas as pd
import pytest
from databallpy.optimization.constraints import TTIConstraint

from looseball.race import ConstantAccelerationModel, ReachModel, race_players, reach_model, team_summary


class _Game:
    def get_column_ids(self):
        return ["home_1"]


def _package(turning_penalty):
    frame = pd.Series({"home_1_x": 0.0, "home_1_y": 0.0, "home_1_vx": 0.0, "home_1_vy": 0.0})
    return TTIConstraint(_Game(), frame, turning_penalty=turning_penalty)


@pytest.mark.parametrize("penalty", ["shaw", "pleuler"])
def test_reach_model_matches_the_package_class(penalty):
    rng = np.random.default_rng(1)
    pos, vel = rng.uniform(-20, 20, (50, 2)), rng.uniform(-6, 6, (50, 2))
    target = np.array([3.0, -4.0])
    ours = ReachModel(penalty).reach_times(pos, vel, target)
    theirs = [_package(penalty).tti(p, target, v) for p, v in zip(pos, vel)]
    assert np.allclose(ours, theirs)


def test_movement_towards_the_target_is_faster_and_away_is_slower():
    m = ReachModel()
    pos = np.array([[0.0, 0.0]] * 3)
    vel = np.array([[0.0, 0.0], [4.0, 0.0], [-4.0, 0.0]])
    static, toward, away = m.reach_times(pos, vel, (10.0, 0.0))
    assert static == pytest.approx(2.7)
    assert toward < static < away
    assert m.empty_team_time(15.0) == pytest.approx(3.7)
    with pytest.raises(ValueError):
        ReachModel("spline")


def _anchor_frame():
    return pd.DataFrame(
        {
            "player_id": [1, 2, 3, 4, 5],
            "x": [2.0, 8.0, 30.0, -5.0, 0.0],
            "y": [0.0, 0.0, 0.0, 0.0, 12.0],
            "vx": [-3.0, 0.0, 0.0, np.nan, 0.0],
            "vy": [0.0, 0.0, 0.0, np.nan, -4.0],
            "is_detected": [True, False, True, True, True],
        }
    )


TEAM_OF = pd.Series({1: 10, 2: 10, 3: 10, 4: 20, 5: 20})


def test_race_players_radius_sides_flags_and_missing_velocity():
    race = race_players(_anchor_frame(), (0.0, 0.0), 10, TEAM_OF, {5}, 15.0, ReachModel())
    assert set(race["player_id"]) == {1, 2, 4, 5}  # player 3 is 30 m away
    assert dict(zip(race["player_id"], race["side"])) == {
        1: "releasing",
        2: "releasing",
        4: "other",
        5: "other",
    }
    assert race.loc[race["player_id"] == 5, "is_gk"].item()
    assert race.loc[race["player_id"] == 4, "velocity_missing"].item()
    p4 = race[race["player_id"] == 4].iloc[0]
    assert p4["t_dynamic"] == pytest.approx(p4["t_static"])  # missing velocity counts as zero
    dropped = race_players(
        _anchor_frame(), (0.0, 0.0), 10, TEAM_OF, {5}, 15.0, ReachModel(), drop_extrapolated=True
    )
    assert 2 not in set(dropped["player_id"])


def test_team_summary_best_times_and_empty_team():
    m = ReachModel()
    race = race_players(_anchor_frame(), (0.0, 0.0), 10, TEAM_OF, {5}, 15.0, m)
    s = team_summary(race, 15.0, m)
    rel = race[race["side"] == "releasing"]
    assert s["best_dynamic_releasing"] == pytest.approx(rel["t_dynamic"].min())
    assert s["nearest_releasing"] == pytest.approx(2.0) and s["nearest_other"] == pytest.approx(5.0)
    assert (s["n_releasing"], s["n_other"], s["n_gk"], s["n_extrapolated"]) == (2, 2, 1, 1)
    only_releasing = race[race["side"] == "releasing"]
    e = team_summary(only_releasing, 15.0, m)
    assert e["empty_other"] and not e["empty_releasing"]
    assert e["best_static_other"] == pytest.approx(3.7) and e["nearest_other"] == pytest.approx(15.0)


def test_constant_acceleration_closed_form_values():
    m = ConstantAccelerationModel()
    pos = np.zeros((5, 2))
    vel = np.array([[0.0, 0.0], [5.0, 0.0], [-2.0, 0.0], [0.0, 4.0], [7.0, 0.0]])
    t = m.reach_times(pos, vel, (10.0, 0.0))
    # standing: 5/3 s to the cap covering 25/6 m, the rest at 5 m/s
    assert t[0] == pytest.approx(5 / 3 + (10 - 25 / 6) / 5)
    assert t[1] == pytest.approx(2.0)  # already at the cap, straight at the target
    assert t[2] == pytest.approx(7 / 3 + (10 - 3.5) / 5)  # first reverses from -2 m/s
    assert t[3] == pytest.approx(t[0])  # sideways velocity is ignored
    assert t[4] == pytest.approx(2.0)  # projected speed above the cap starts at the cap
    short = m.reach_times(np.zeros((1, 2)), np.zeros((1, 2)), (1.0, 0.0))[0]
    assert short == pytest.approx(np.sqrt(2 / 3))  # 1 m before reaching the cap
    assert m.empty_team_time(15.0) == pytest.approx(5 / 3 + (15 - 25 / 6) / 5)
    assert m.reach_times(np.array([[3.0, 4.0]]), np.zeros((1, 2)), (3.0, 4.0))[0] == 0.0


def test_reach_model_factory_and_reaction_time_variant():
    assert isinstance(reach_model("constant_acceleration"), ConstantAccelerationModel)
    fast = reach_model("databallpy", reaction_time=0.35)
    assert fast.reach_times(np.zeros((1, 2)), np.zeros((1, 2)), (10.0, 0.0))[0] == pytest.approx(0.35 + 2.0)
    assert fast.empty_team_time(15.0) == pytest.approx(0.35 + 3.0)
    with pytest.raises(ValueError):
        reach_model("spline")
