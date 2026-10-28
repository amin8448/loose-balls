"""DataBallPy's time-to-intercept constraint (develop, PR #408), called as the package defines it."""

import numpy as np
import pandas as pd
import pytest
from databallpy.optimization.constraints import TTIConstraint


class _Game:
    """Stand-in for databallpy.game.Game: the constraint only reads get_column_ids()."""

    def get_column_ids(self):
        return ["home_1"]


def _constraint(turning_penalty):
    frame = pd.Series({"home_1_x": 0.0, "home_1_y": 0.0, "home_1_vx": 5.0, "home_1_vy": 0.0})
    return TTIConstraint(_Game(), frame, turning_penalty=turning_penalty)


def test_shaw_and_pleuler_give_different_times():
    origin, velocity, destination = np.array([0.0, 0.0]), np.array([5.0, 0.0]), np.array([0.0, 10.0])
    shaw = _constraint("shaw").tti(origin, destination, velocity)
    pleuler = _constraint("pleuler").tti(origin, destination, velocity)
    # Shaw: 0.7 + |(0, 10) - (3.5, 0)| / 5; Pleuler adds |v| * angle / pi = 5 * (pi / 2) / pi
    assert shaw == pytest.approx(0.7 + np.hypot(3.5, 10.0) / 5.0)
    assert pleuler == pytest.approx(shaw + 2.5)
    assert pleuler != shaw


def test_package_defaults_and_standing_player():
    c = _constraint("shaw")
    assert (c.reaction_time, c.max_velocity, c.turning_penalty) == (0.7, 5.0, "shaw")
    t = c.tti(np.array([0.0, 0.0]), np.array([10.0, 0.0]), np.array([0.0, 0.0]))
    assert t == pytest.approx(0.7 + 10.0 / 5.0)


def test_unknown_turning_penalty_is_refused():
    with pytest.raises(ValueError):
        _constraint("spline")
