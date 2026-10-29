"""The decomposition (step 2, D6): decompose.

With a team's own probabilities ps (static) and pd (dynamic):
- deficit of the team that lost: positioning 1 - ps, reading ps - pd, after the anchor pd;
- credit of the team that won: positioning ps, reading pd - ps, after the anchor 1 - pd.
Verdict for a lost ball, from the loser's ps and pd: positioning if ps < 0.5; reading if
ps >= 0.5 and pd < 0.5; after the anchor otherwise. Immediate episodes (lead under 0.5 s) are
reported, not decomposed.
"""

import numpy as np
import pandas as pd

SHARES = ("positioning", "reading", "after the anchor")
VERDICT_LINE = 0.5


def deficit_shares(ps, pd_) -> pd.DataFrame:
    ps, pd_ = np.asarray(ps, float), np.asarray(pd_, float)
    return pd.DataFrame({"positioning": 1 - ps, "reading": ps - pd_, "after the anchor": pd_})


def credit_shares(ps, pd_) -> pd.DataFrame:
    ps, pd_ = np.asarray(ps, float), np.asarray(pd_, float)
    return pd.DataFrame({"positioning": ps, "reading": pd_ - ps, "after the anchor": 1 - pd_})


def verdict(ps, pd_) -> np.ndarray:
    ps, pd_ = np.asarray(ps, float), np.asarray(pd_, float)
    return np.where(
        ps < VERDICT_LINE, "positioning", np.where(pd_ < VERDICT_LINE, "reading", "after the anchor")
    )


def decompose(expectations: pd.DataFrame, outcomes: pd.DataFrame) -> pd.DataFrame:
    """Deficit and credit shares and the categorical verdict per episode (DESIGN.md
    "Decomposition", step 2 D6).

    Inputs: expectations from expectations(); outcomes with match_id, seq_i and winning_team
    (the team of possession i+1), and optionally immediate (bool; such episodes get the verdict
    "immediate" and no shares). Output, one row per episode: match_id, seq_i, p_static and
    p_dynamic (releasing team), releasing_won, immediate, loser_side, losing_team,
    winning_team, p_static_loser, p_dynamic_loser, the three "deficit ..." and three
    "credit ..." shares, and verdict. An episode's credit for the winner equals its deficit for
    the loser; team views differ in which episodes enter.
    """
    key = ["match_id", "seq_i"]
    rel = expectations[expectations["side"] == "releasing"].set_index(key)
    oth = expectations[expectations["side"] == "other"].set_index(key)
    o = outcomes.set_index(key).reindex(rel.index)
    ps, pd_ = rel["p_static"].to_numpy(float), rel["p_dynamic"].to_numpy(float)
    won = o["winning_team"].to_numpy() == rel["team_id"].to_numpy()
    immediate = o["immediate"].fillna(False).to_numpy(bool) if "immediate" in o else np.zeros(len(rel), bool)
    ps_loser = np.where(won, 1 - ps, ps)
    pd_loser = np.where(won, 1 - pd_, pd_)
    out = pd.DataFrame(
        {
            "match_id": rel.index.get_level_values(0),
            "seq_i": rel.index.get_level_values(1),
            "p_static": ps,
            "p_dynamic": pd_,
            "releasing_won": won.astype(int),
            "immediate": immediate,
            "loser_side": np.where(won, "other", "releasing"),
            "losing_team": np.where(
                won, oth["team_id"].reindex(rel.index).to_numpy(), rel["team_id"].to_numpy()
            ),
            "winning_team": o["winning_team"].to_numpy(),
            "p_static_loser": ps_loser,
            "p_dynamic_loser": pd_loser,
        }
    )
    d = deficit_shares(ps_loser, pd_loser).add_prefix("deficit ")
    c = credit_shares(1 - ps_loser, 1 - pd_loser).add_prefix("credit ")
    out = pd.concat([out, d, c], axis=1)
    out["losing_team"] = out["losing_team"].astype("Int64")
    out["winning_team"] = out["winning_team"].astype("Int64")
    out.loc[immediate, [*d.columns, *c.columns]] = np.nan
    out["verdict"] = np.where(immediate, "immediate", verdict(ps_loser, pd_loser))
    return out
