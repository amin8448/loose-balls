import numpy as np
import pandas as pd
import pytest

from looseball_research import expectation as ex


def _simulate(n, a, b, seed=0, matches=5):
    rng = np.random.default_rng(seed)
    x = rng.uniform(-3, 3, n)
    y = (rng.uniform(size=n) < ex.sigmoid(a + b * x)).astype(float)
    return x, y, rng.integers(0, matches, n)


def test_logistic_fit_recovers_parameters():
    x, y, _ = _simulate(40000, 0.5, 2.0)
    a, b = ex.fit(x, y, intercept=True)
    assert a == pytest.approx(0.5, abs=0.06) and b == pytest.approx(2.0, abs=0.08)


def test_softmax_fit_has_no_intercept_and_matches_the_two_team_softmax():
    x, y, _ = _simulate(40000, 0.0, 1.5, seed=1)
    a, b = ex.fit(x, y, intercept=False)
    assert a == 0.0 and b == pytest.approx(1.5, abs=0.06)
    t_rel, t_oth, temp = 1.2, 2.0, 1 / b
    softmax = np.exp(-t_rel / temp) / (np.exp(-t_rel / temp) + np.exp(-t_oth / temp))
    assert ex.predict((0.0, b), t_oth - t_rel) == pytest.approx(softmax)


def test_log_loss_reference_values():
    assert ex.log_loss([1, 0, 1, 0], [0.5] * 4) == pytest.approx(np.log(2))
    assert ex.log_loss([1, 0], [1.0, 0.0]) < 1e-9


def test_leave_one_match_out_uses_only_other_matches():
    x, y, m = _simulate(3000, 0.2, 1.0, seed=2)
    p1 = ex.leave_one_match_out(x, y, m, intercept=True)
    y2 = y.copy()
    y2[m == 0] = 1 - y2[m == 0]  # change the outcomes of match 0 only
    p2 = ex.leave_one_match_out(x, y2, m, intercept=True)
    assert np.allclose(p1[m == 0], p2[m == 0])
    assert not np.allclose(p1[m != 0], p2[m != 0])


def test_features_are_oriented_to_the_releasing_team():
    s = pd.DataFrame(
        {
            "best_dynamic_releasing": [1.0],
            "best_dynamic_other": [1.8],
            "best_static_releasing": [1.5],
            "best_static_other": [1.4],
            "n_releasing": [3],
            "n_other": [1],
            "nearest_releasing": [2.0],
            "nearest_other": [6.5],
        }
    )
    f = ex.features(s)
    assert (
        f.loc[0, "dt"] == pytest.approx(0.8) and f.loc[0, "dn"] == 2 and f.loc[0, "dd"] == pytest.approx(4.5)
    )
    assert ex.features(s, "static").loc[0, "dt"] == pytest.approx(-0.1)


def test_compare_and_calibration_shapes():
    x, y, m = _simulate(2000, 0.0, 1.2, seed=3)
    feats = pd.DataFrame({"dt": x, "dn": np.round(x), "dd": x * 2})
    table, preds = ex.compare(feats, y, m)
    assert list(table["model"]) == list(ex.MODELS) and preds.notna().all().all()
    cal = ex.calibration(preds["logistic"], y)
    assert len(cal) == 5 and cal["episodes"].sum() == len(y)
