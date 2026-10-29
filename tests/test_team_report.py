import numpy as np
import pandas as pd
import pytest

from looseball import team_report
from looseball.decompose import SHARES


def _decomposed(n=240, seed=0):
    rng = np.random.default_rng(seed)
    t = pd.DataFrame(
        {"match_id": rng.integers(0, 4, n), "seq_i": np.arange(n), "losing_team": rng.choice([1, 2], n)}
    )
    t["winning_team"] = 3 - t["losing_team"]
    t["verdict"] = rng.choice(list(SHARES), n, p=[0.7, 0.1, 0.2])
    for kind in ("deficit", "credit"):
        a = rng.uniform(0, 1, n)
        t[f"{kind} positioning"], t[f"{kind} reading"], t[f"{kind} after the anchor"] = a, 0.0, 1 - a
    return t


def test_categorical_and_continuous_team_shares():
    t = _decomposed()
    r = team_report(t, n_boot=300, seed=1, team_names={1: "One", 2: "Two"}, matches_per_team={1: 4, 2: 2})
    v = r["verdicts"].set_index("team")
    assert list(v["name"]) == ["One", "Two"] and list(v["small sample"]) == [False, True]
    lost1 = t[t["losing_team"] == 1]
    assert v.loc[1, "positioning"] == pytest.approx((lost1["verdict"] == "positioning").mean())
    assert v.loc[1, "positioning lo"] < v.loc[1, "positioning"] < v.loc[1, "positioning hi"]
    assert np.allclose(v[list(SHARES)].sum(axis=1), 1)
    s = r["shares"].set_index("team")
    assert s.loc[1, "deficit positioning"] == pytest.approx(lost1["deficit positioning"].mean())
    assert s["lost"].sum() == len(t) and s["won"].sum() == len(t)
    assert r["seed"] == 1 and r["replicates"] == 300


def test_same_seed_same_intervals_and_immediate_left_out():
    t = _decomposed()
    t.loc[:9, "verdict"] = "immediate"
    a, b = team_report(t, n_boot=100, seed=7), team_report(t, n_boot=100, seed=7)
    assert a["verdicts"].equals(b["verdicts"]) and a["shares"].equals(b["shares"])
    assert a["verdicts"]["lost"].sum() == len(t) - 10
    assert (a["verdicts"]["matches"] == 4).all()  # counted from the episodes when not given
