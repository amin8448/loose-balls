import numpy as np
import pandas as pd
import pytest

from looseball import expectation as ex
from looseball import expectations


def _reach():
    """Episode 0: releasing team best 1.2 s static and 1.0 s dynamic, other team 1.5 and 1.9 s.
    Episode 1: the other team is empty (time 3.7 s, distance 15 m)."""
    rows = [
        (0, "releasing", 10, 4.0, 1.5, 1.2, 1.0, False),
        (0, "releasing", 10, 9.0, 2.5, 2.5, 2.4, False),
        (0, "other", 20, 6.0, 1.9, 1.5, 1.9, False),
        (1, "releasing", 10, 3.0, 1.3, 1.3, 1.1, False),
        (1, "other", 20, 15.0, None, 3.7, 3.7, True),
    ]
    r = pd.DataFrame(
        rows, columns=["seq_i", "side", "team_id", "dist", "_", "t_static", "t_dynamic", "empty_team"]
    )
    return r.drop(columns="_").assign(match_id=1, detected=True)


def test_expectations_follow_the_frozen_softmax():
    b = ex.frozen_parameters()["chosen"]["b"]
    e = expectations(_reach()).set_index(["seq_i", "side"])
    assert e.loc[(0, "releasing"), "p_static"] == pytest.approx(1 / (1 + np.exp(-b * (1.5 - 1.2))))
    assert e.loc[(0, "releasing"), "p_dynamic"] == pytest.approx(1 / (1 + np.exp(-b * (1.9 - 1.0))))
    assert e.loc[(0, "other"), "p_dynamic"] == pytest.approx(1 - e.loc[(0, "releasing"), "p_dynamic"])
    assert e.loc[(1, "releasing"), "p_static"] == pytest.approx(1 / (1 + np.exp(-b * (3.7 - 1.3))))
    assert list(e.reset_index()["team_id"]) == [10, 20, 10, 20]


def test_equal_best_times_give_one_half_whatever_the_slope():
    r = _reach()
    r.loc[2, ["t_static", "t_dynamic"]] = [1.2, 1.0]  # other team's best equals the releasing team's
    e = expectations(r, {"chosen": {"a": 0.0, "b": 7.3}}).set_index(["seq_i", "side"])
    assert e.loc[(0, "releasing"), "p_static"] == 0.5 and e.loc[(0, "releasing"), "p_dynamic"] == 0.5


def test_race_summary_and_baselines():
    s = ex.race_summary(_reach()).set_index("seq_i")
    assert (s.loc[0, "n_releasing"], s.loc[0, "n_other"], s.loc[1, "n_other"]) == (2, 1, 0)
    assert s.loc[1, "nearest_other"] == 15.0 and s.loc[1, "best_dynamic_other"] == 3.7
    par = ex.frozen_parameters()
    bl = ex.baselines(_reach()).set_index("seq_i")
    assert bl.loc[0, "p_B0"] == pytest.approx(1 / (1 + np.exp(-(par["B0"]["a"] + par["B0"]["b"] * 1))))
    assert bl.loc[0, "p_B1"] == pytest.approx(1 / (1 + np.exp(-(par["B1"]["a"] + par["B1"]["b"] * 2.0))))


def test_fit_recovers_parameters_and_refit_runs():
    rng = np.random.default_rng(0)
    x = rng.uniform(-2, 2, 40000)
    y = (rng.uniform(size=x.size) < ex.sigmoid(2.9 * x)).astype(float)
    a, b = ex.fit(x, y, intercept=False)
    assert a == 0.0 and b == pytest.approx(2.9, abs=0.1)
    out = ex.refit(_reach(), [1, 0], model="softmax")
    assert set(out) == {"feature", "intercept", "a", "b"} and out["intercept"] is False


def test_log_loss_and_calibration():
    assert ex.log_loss([1, 0], [0.5, 0.5]) == pytest.approx(np.log(2))
    cal = ex.calibration([0.05, 0.15, 0.95], [0, 1, 1])
    assert list(cal["episodes"]) == [2, 0, 0, 0, 1]
