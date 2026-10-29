"""Expectation model (step 2, D5) and the baselines B0 and B1.

Every probability is that the releasing team (team of possession i) wins the loose ball.
Features, from the race team summary (race.team_summary):
- dt: best time of the other team minus best time of the releasing team (static or dynamic)
- dn: players of the releasing team in the race minus players of the other team (B0)
- dd: nearest distance of the other team minus nearest distance of the releasing team (B1)

Forms (decided before any fit, AUDIT.md step 2 setup):
- softmax: sigmoid(b * dt), one parameter, temperature T = 1 / b. This is the two-team softmax
  exp(-t_rel / T) / (exp(-t_rel / T) + exp(-t_other / T)).
- logistic: sigmoid(a + b * dt).
- B0: sigmoid(a + b * dn); B1: sigmoid(a + b * dd).
Fitting is maximum likelihood. Model choice uses leave-one-match-out log-loss.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize

# model name: (feature, has intercept)
MODELS = {
    "softmax": ("dt", False),
    "logistic": ("dt", True),
    "B0": ("dn", True),
    "B1": ("dd", True),
}
EPS = 1e-12


def features(summary: pd.DataFrame, times: str = "dynamic") -> pd.DataFrame:
    """dt (from static or dynamic best times), dn and dd for each episode of a race summary."""
    return pd.DataFrame(
        {
            "dt": summary[f"best_{times}_other"] - summary[f"best_{times}_releasing"],
            "dn": summary["n_releasing"] - summary["n_other"],
            "dd": summary["nearest_other"] - summary["nearest_releasing"],
        },
        index=summary.index,
    )


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.asarray(z, dtype=float)))


def log_loss(y, p) -> float:
    y, p = np.asarray(y, float), np.clip(np.asarray(p, float), EPS, 1 - EPS)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def fit(x, y, intercept: bool) -> tuple[float, float]:
    """Maximum-likelihood (a, b) of sigmoid(a + b x); a is 0 without intercept."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    design = np.column_stack([np.ones_like(x), x]) if intercept else x[:, None]

    def nll(theta):
        z = design @ theta
        return np.sum(np.logaddexp(0.0, z) - y * z), design.T @ (sigmoid(z) - y)

    theta = minimize(nll, np.zeros(design.shape[1]), jac=True, method="BFGS").x
    return (float(theta[0]), float(theta[1])) if intercept else (0.0, float(theta[0]))


def predict(params: tuple[float, float], x) -> np.ndarray:
    a, b = params
    return sigmoid(a + b * np.asarray(x, float))


def leave_one_match_out(x, y, match, intercept: bool) -> np.ndarray:
    """Out-of-fold probabilities: each match predicted from a fit on the other matches."""
    x, y, match = np.asarray(x, float), np.asarray(y, float), np.asarray(match)
    p = np.full(len(x), np.nan)
    for m in np.unique(match):
        held = match == m
        p[held] = predict(fit(x[~held], y[~held], intercept), x[held])
    return p


def compare(feats: pd.DataFrame, y, match) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Leave-one-match-out log-loss of every model, pooled and per match, and the predictions."""
    y, match = np.asarray(y, float), np.asarray(match)
    preds = pd.DataFrame(index=feats.index)
    rows = []
    for name, (col, intercept) in MODELS.items():
        p = leave_one_match_out(feats[col], y, match, intercept)
        preds[name] = p
        row = {"model": name, "pooled": log_loss(y, p)}
        row.update({str(m): log_loss(y[match == m], p[match == m]) for m in np.unique(match)})
        rows.append(row)
    return pd.DataFrame(rows), preds


def calibration(p, y, bins: int = 5) -> pd.DataFrame:
    """Equal-width bins of predicted probability: count, mean prediction, observed share."""
    p, y = np.asarray(p, float), np.asarray(y, float)
    edges = np.linspace(0, 1, bins + 1)
    k = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    rows = []
    for i in range(bins):
        sel = k == i
        rows.append(
            {
                "bin": f"{edges[i]:.1f} to {edges[i + 1]:.1f}",
                "episodes": int(sel.sum()),
                "mean predicted": p[sel].mean() if sel.any() else np.nan,
                "observed share": y[sel].mean() if sel.any() else np.nan,
            }
        )
    return pd.DataFrame(rows)
