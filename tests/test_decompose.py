import numpy as np
import pandas as pd
import pytest

from looseball import decompose as dc


def test_shares_follow_the_definitions_and_sum_to_one():
    d = dc.deficit_shares([0.7, 0.2], [0.4, 0.6])
    assert np.allclose(d["positioning"], [0.3, 0.8])
    assert np.allclose(d["reading"], [0.3, -0.4])  # negative when movement helped
    assert np.allclose(d["after the anchor"], [0.4, 0.6])
    c = dc.credit_shares([0.7, 0.2], [0.4, 0.6])
    assert np.allclose(d.sum(axis=1), 1) and np.allclose(c.sum(axis=1), 1)
    assert np.allclose(c["reading"], [-0.3, 0.4])


def test_verdict_boundaries():
    v = dc.verdict([0.49, 0.5, 0.5, 0.9], [0.9, 0.49, 0.5, 0.1])
    assert list(v) == ["positioning", "reading", "after the anchor", "reading"]


def test_decompose_orients_to_the_loser_and_marks_immediate():
    out = dc.decompose(
        p_static_rel=[0.8, 0.8, 0.3],
        p_dynamic_rel=[0.6, 0.6, 0.3],
        releasing_won=[True, False, True],
        lead=[1.0, 1.0, 0.4],
    )
    # episode 0: releasing team won, loser is the other team with ps 0.2, pd 0.4
    assert out.loc[0, "loser_side"] == "other"
    assert out.loc[0, "p_static_loser"] == pytest.approx(0.2) and out.loc[0, "verdict"] == "positioning"
    # episode 1: releasing team lost with ps 0.8, pd 0.6
    assert out.loc[1, "verdict"] == "after the anchor"
    assert out.loc[1, "deficit reading"] == pytest.approx(0.2)
    # the winner's credit equals the loser's deficit in every episode
    for s in dc.SHARES:
        assert out.loc[:1, f"credit {s}"].tolist() == pytest.approx(out.loc[:1, f"deficit {s}"].tolist())
    assert (
        out.loc[2, "verdict"] == "immediate" and out.loc[2, [f"deficit {s}" for s in dc.SHARES]].isna().all()
    )


def test_team_shares_counts_means_and_intervals():
    rng = np.random.default_rng(0)
    n = 300
    t = pd.DataFrame(
        {
            "match_id": rng.integers(0, 3, n),
            "losing_team": rng.choice([1, 2], n),
        }
    )
    t["winning_team"] = 3 - t["losing_team"]
    for kind in ("deficit", "credit"):
        a = rng.uniform(0, 1, n)
        t[f"{kind} positioning"], t[f"{kind} reading"], t[f"{kind} after the anchor"] = a, 0.0, 1 - a
    out = dc.team_shares(t, n_boot=200, seed=1)
    assert list(out["team"]) == [1, 2]
    assert out["lost"].sum() == n and out["won"].sum() == n
    row = out.iloc[0]
    assert row["deficit positioning"] == pytest.approx(
        t.loc[t["losing_team"] == 1, "deficit positioning"].mean()
    )
    assert row["deficit positioning lo"] < row["deficit positioning"] < row["deficit positioning hi"]
    again = dc.team_shares(t, n_boot=200, seed=1)
    assert again.equals(out)
