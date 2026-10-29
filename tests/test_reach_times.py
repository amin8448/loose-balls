import numpy as np
import pandas as pd
import pytest
import synthetic as syn
from databallpy.optimization.constraints import TTIConstraint

from looseball import reach_times
from looseball.race import ConstantAccelerationModel, ReachModel
from looseball.velocities import smooth_velocities


class _Game:
    def get_column_ids(self):
        return ["home_1"]


@pytest.mark.parametrize("penalty", ["shaw", "pleuler"])
def test_reach_model_equals_the_package_class(penalty):
    frame = pd.Series({"home_1_x": 0.0, "home_1_y": 0.0, "home_1_vx": 0.0, "home_1_vy": 0.0})
    package = TTIConstraint(_Game(), frame, turning_penalty=penalty)
    rng = np.random.default_rng(3)
    pos, vel, target = rng.uniform(-20, 20, (40, 2)), rng.uniform(-6, 6, (40, 2)), np.array([2.0, -1.0])
    ours = ReachModel(penalty).reach_times(pos, vel, target)
    assert np.allclose(ours, [package.tti(p, target, v) for p, v in zip(pos, vel)])


def test_smoothed_velocity_is_exact_on_a_straight_track():
    f = np.arange(30)
    v = smooth_velocities(
        pd.DataFrame({"frame": f, "column_id": "home_1", "x": 1 + 0.3 * f, "y": 2 - 0.4 * f})
    )
    assert np.allclose(v["vx"], 3.0) and np.allclose(v["vy"], -4.0)


def _fixture(n=60):
    t = np.arange(n)
    players = {
        "home_1": (
            5.0 - 0.2 * (t - 30),
            np.zeros(n),
            np.ones(n, bool),
        ),  # at (5, 0) on frame 30, moving -2 m/s in x
        "away_2": (np.zeros(n), np.full(n, 8.0), np.ones(n, bool)),  # standing 8 m away
        "home_3": (np.zeros(n), np.full(n, -12.0), np.zeros(n, bool)),  # 12 m away, not detected
        "away_4": (np.full(n, 18.0), np.zeros(n), np.ones(n, bool)),  # 18 m away
    }
    tr = syn.tracking(n, np.zeros((n, 2)), players)
    ep = pd.DataFrame([{"match_id": 1, "seq_i": 0, "anchored": True, "anchor_frame": 30, "pickup_frame": 55,
                        "pickup_x": 0.0, "pickup_y": 0.0, "team_id_i": 10}])  # fmt: skip
    return ep, tr


def test_reach_times_values_sides_and_flags():
    ep, tr = _fixture()
    r = reach_times(ep, tr, syn.PLAYERS).set_index("column_id")
    assert set(r.index) == {"home_1", "away_2", "home_3"}  # away_4 is beyond 15 m
    assert r.loc["home_1", "t_static"] == pytest.approx(0.7 + 5 / 5)
    assert r.loc["home_1", "t_dynamic"] == pytest.approx(0.7 + (5 - 2 * 0.7) / 5)
    assert r.loc["away_2", "t_dynamic"] == pytest.approx(0.7 + 8 / 5)
    assert r.loc["home_1", "side"] == "releasing" and r.loc["away_2", "side"] == "other"
    assert not r.loc["home_3", "detected"] and not r["empty_team"].any()
    assert np.allclose(r["lead_s"], 2.5) and (r["radius_m"] == 15.0).all()


def test_variants_and_the_empty_team_row():
    ep, tr = _fixture()
    dropped = reach_times(ep, tr, syn.PLAYERS, drop_extrapolated=True)
    assert "home_3" not in set(dropped["column_id"])
    grown = reach_times(ep, tr, syn.PLAYERS, growing_speed=8.0)  # max(15, 8 x 2.5) = 20 m
    assert "away_4" in set(grown["column_id"]) and (grown["radius_m"] == 20.0).all()
    shifted = reach_times(ep, tr, syn.PLAYERS, anchor_shift=2)
    assert (shifted["anchor_frame"] == 32).all() and np.allclose(shifted["lead_s"], 2.3)
    small = reach_times(ep, tr, syn.PLAYERS, radius=6.0)  # only home_1: the other team is empty
    empty = small[small["empty_team"]].iloc[0]
    assert empty["side"] == "other" and empty["team_id"] == 20
    assert empty["t_static"] == pytest.approx(0.7 + 6 / 5) and empty["dist"] == 6.0
    pleuler = reach_times(ep, tr, syn.PLAYERS, turning_penalty="pleuler").set_index("column_id")
    assert pleuler.loc["home_1", "t_dynamic"] == pytest.approx(0.7 + (5 - 2 * 0.7) / 5)  # straight at it


def test_constant_acceleration_option():
    ep, tr = _fixture()
    r = reach_times(ep, tr, syn.PLAYERS, model="constant_acceleration").set_index("column_id")
    ca = ConstantAccelerationModel()
    assert r.loc["away_2", "t_dynamic"] == pytest.approx(
        ca.reach_times(np.array([[0.0, 8.0]]), np.zeros((1, 2)), (0, 0))[0]
    )
    assert r.loc["away_2", "t_dynamic"] == pytest.approx(5 / 3 + (8 - 25 / 6) / 5)
