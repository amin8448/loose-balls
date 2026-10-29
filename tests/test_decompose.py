import numpy as np
import pandas as pd
import pytest

from looseball import decompose
from looseball.decompose import SHARES, verdict


def _expectations(ps_rel, pd_rel):
    rows = []
    for i, (s, d) in enumerate(zip(ps_rel, pd_rel)):
        rows.append(
            {"match_id": 1, "seq_i": i, "side": "releasing", "team_id": 10, "p_static": s, "p_dynamic": d}
        )
        rows.append(
            {"match_id": 1, "seq_i": i, "side": "other", "team_id": 20, "p_static": 1 - s, "p_dynamic": 1 - d}
        )
    return pd.DataFrame(rows)


def test_shares_verdicts_and_orientation_to_the_loser():
    e = _expectations([0.8, 0.8, 0.3, 0.6], [0.6, 0.6, 0.3, 0.2])
    o = pd.DataFrame({"match_id": 1, "seq_i": [0, 1, 2, 3], "winning_team": [10, 20, 10, 20]})
    d = decompose(e, o).set_index("seq_i")
    # 0: releasing team won; loser is the other team with ps 0.2, pd 0.4
    assert d.loc[0, "losing_team"] == 20 and d.loc[0, "verdict"] == "positioning"
    assert d.loc[0, "deficit positioning"] == pytest.approx(0.8) and d.loc[
        0, "deficit reading"
    ] == pytest.approx(-0.2)
    # 1: releasing team lost with ps 0.8, pd 0.6
    assert d.loc[1, "losing_team"] == 10 and d.loc[1, "verdict"] == "after the anchor"
    # 3: releasing team lost a ball it was placed to win (ps 0.6) but movement turned (pd 0.2)
    assert d.loc[3, "verdict"] == "reading"
    shares = d[[f"deficit {s}" for s in SHARES]]
    assert np.allclose(shares.sum(axis=1), 1)
    for s in SHARES:
        assert np.allclose(d[f"credit {s}"], d[f"deficit {s}"])


def test_verdict_boundaries_and_the_immediate_class():
    assert list(verdict([0.49, 0.5, 0.5], [0.9, 0.49, 0.5])) == ["positioning", "reading", "after the anchor"]
    e = _expectations([0.7], [0.4])
    o = pd.DataFrame({"match_id": [1], "seq_i": [0], "winning_team": [20], "immediate": [True]})
    d = decompose(e, o).iloc[0]
    assert d["verdict"] == "immediate" and np.isnan(d["deficit positioning"])
