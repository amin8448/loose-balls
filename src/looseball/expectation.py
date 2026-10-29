"""Expectation model (step 2, D5): expectations, with the frozen parameters shipped as package data.

Every fitted probability is the releasing team's (the team of possession i). Features from the
race summary: dt, the other team's best reach time minus the releasing team's; dn, players in
the race of the releasing team minus the other team's (baseline B0); dd, nearest distance of
the other team minus the releasing team's (baseline B1). The frozen D5 model is the softmax,
p = sigmoid(b x dt), temperature 1 / b. refit() is never called by the reproduction path.
"""

import json
from importlib import resources

import numpy as np
import pandas as pd
from scipy.optimize import minimize

MODELS = {"softmax": ("dt", False), "logistic": ("dt", True), "B0": ("dn", True), "B1": ("dd", True)}
SIDES = ("releasing", "other")
EPS = 1e-12


def frozen_parameters() -> dict:
    """The parameters frozen before MT1 (audit/frozen_parameters.json), shipped with the package."""
    return json.loads(resources.files("looseball").joinpath("data/frozen_parameters.json").read_text())


def frozen_static_temperature() -> dict:
    """The separate static temperature (step 3, 3c.0; exploration-only, report-only), shipped with
    the package. It benchmarks V2; the decomposition keeps the shared temperature."""
    return json.loads(
        resources.files("looseball").joinpath("data/frozen_static_temperature.json").read_text()
    )


def sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.asarray(z, dtype=float)))


def predict(params: tuple[float, float], x) -> np.ndarray:
    a, b = params
    return sigmoid(a + b * np.asarray(x, float))


def log_loss(y, p) -> float:
    y, p = np.asarray(y, float), np.clip(np.asarray(p, float), EPS, 1 - EPS)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def race_summary(reach: pd.DataFrame) -> pd.DataFrame:
    """Per episode and side: players in the race, detected players, best static and dynamic reach
    time and nearest distance (an empty team's row gives the empty-team time and the radius)."""
    rows = []
    for (m, s), g in reach.groupby(["match_id", "seq_i"], sort=True):
        out = {"match_id": m, "seq_i": s}
        for side in SIDES:
            d = g[g["side"] == side]
            players = d[~d["empty_team"]]
            out[f"team_id_{side}"] = d["team_id"].iloc[0]
            out[f"n_{side}"] = len(players)
            out[f"n_detected_{side}"] = int(players["detected"].astype(bool).sum())
            out[f"best_static_{side}"] = d["t_static"].min()
            out[f"best_dynamic_{side}"] = d["t_dynamic"].min()
            out[f"nearest_{side}"] = d["dist"].min()
        rows.append(out)
    return pd.DataFrame(rows)


def features(summary: pd.DataFrame, times: str = "dynamic") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "dt": summary[f"best_{times}_other"] - summary[f"best_{times}_releasing"],
            "dn": summary["n_releasing"] - summary["n_other"],
            "dd": summary["nearest_other"] - summary["nearest_releasing"],
        },
        index=summary.index,
    )


def expectations(reach: pd.DataFrame, parameters: dict | None = None) -> pd.DataFrame:
    """p_static and p_dynamic per team per episode (step 2, D5 and D6; DESIGN.md "Decomposition").

    Inputs: reach from reach_times; parameters as in looseball/data/frozen_parameters.json
    (default: the frozen ones; the "chosen" entry is used). Output: two rows per episode,
    match_id, seq_i, side ("releasing" or "other"), team_id, p_static, p_dynamic; the other
    team's probabilities are one minus the releasing team's.
    """
    par = (parameters or frozen_parameters())["chosen"]
    s = race_summary(reach)
    p_static = predict((par["a"], par["b"]), features(s, "static")["dt"])
    p_dynamic = predict((par["a"], par["b"]), features(s, "dynamic")["dt"])
    rel = pd.DataFrame({"match_id": s["match_id"], "seq_i": s["seq_i"], "side": "releasing",
                        "team_id": s["team_id_releasing"], "p_static": p_static, "p_dynamic": p_dynamic})  # fmt: skip
    oth = rel.assign(side="other", team_id=s["team_id_other"], p_static=1 - p_static, p_dynamic=1 - p_dynamic)
    out = pd.concat([rel, oth], ignore_index=True)
    return out.sort_values(
        ["match_id", "seq_i", "side"], ascending=[True, True, False], kind="stable"
    ).reset_index(drop=True)


def baselines(reach: pd.DataFrame, parameters: dict | None = None) -> pd.DataFrame:
    """Releasing team's probability under the frozen baselines B0 (player count) and B1 (nearest
    distance), used for V1."""
    par = parameters or frozen_parameters()
    s = race_summary(reach)
    f = features(s, "dynamic")
    return pd.DataFrame(
        {
            "match_id": s["match_id"],
            "seq_i": s["seq_i"],
            "p_B0": predict((par["B0"]["a"], par["B0"]["b"]), f["dn"]),
            "p_B1": predict((par["B1"]["a"], par["B1"]["b"]), f["dd"]),
        }
    )


def fit(x, y, intercept: bool) -> tuple[float, float]:
    """Maximum-likelihood (a, b) of sigmoid(a + b x); a is 0 without intercept."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    design = np.column_stack([np.ones_like(x), x]) if intercept else x[:, None]

    def nll(theta):
        z = design @ theta
        return np.sum(np.logaddexp(0.0, z) - y * z), design.T @ (sigmoid(z) - y)

    theta = minimize(nll, np.zeros(design.shape[1]), jac=True, method="BFGS").x
    return (float(theta[0]), float(theta[1])) if intercept else (0.0, float(theta[0]))


def refit(reach: pd.DataFrame, releasing_won, model: str = "softmax") -> dict:
    """Fit one model's parameters on new data (not used by the reproduction path)."""
    col, intercept = MODELS[model]
    a, b = fit(features(race_summary(reach), "dynamic")[col], releasing_won, intercept)
    return {"feature": col, "intercept": intercept, "a": a, "b": b}


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
