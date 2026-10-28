import numpy as np
import pandas as pd
import pytest

from looseball import gate


def test_keep_rule_boundaries():
    kept = gate.keep(
        n_in_race=[0, 20, 20, 10, 10],
        n_detected=[0, 17, 16, 10, 10],
        winner_detected=[True, True, True, True, False],
    )
    # nobody in the race counts as observed; 17 of 20 is exactly 85%; 16 of 20 is not; winner unseen drops
    assert list(kept) == [True, True, False, True, False]


def test_drop_rates_by_column():
    t = pd.DataFrame({"trigger": ["T1", "T1", "T2", "T2", "T2"], "kept": [True, False, True, True, False]})
    r = gate.drop_rates(t, "trigger").set_index("trigger")
    assert r.loc["T1", "drop rate"] == pytest.approx(0.5)
    assert r.loc["T2", "dropped"] == 1 and r.loc["all", "episodes"] == 5


def test_win_share_difference_point_and_interval():
    rng = np.random.default_rng(0)
    n = 1000
    t = pd.DataFrame({"match_id": rng.integers(0, 5, n), "kept": rng.uniform(size=n) < 0.8})
    t["releasing_won"] = np.where(t["kept"], rng.uniform(size=n) < 0.4, rng.uniform(size=n) < 0.6)
    out = gate.win_share_difference(t, n_boot=300, seed=2)
    assert out["difference"] == pytest.approx(out["win share dropped"] - out["win share kept"])
    assert out["lo"] < out["difference"] < out["hi"]
    assert out["lo"] > 0  # a 20 point difference on 1000 episodes is resolved
