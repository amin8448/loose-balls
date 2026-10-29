"""The decomposition (step 2, D6), the immediate class (D1) and team shares (D8).

p_static and p_dynamic are the releasing team's probabilities from the frozen D5 model with
static and dynamic best times. With a team's own probabilities ps and pd:
- deficit of the team that lost: positioning 1 - ps, reading ps - pd, after the anchor pd;
- credit of the team that won: positioning ps, reading pd - ps, after the anchor 1 - pd.
Both sum to 1. Since the two teams' probabilities sum to 1, an episode's credit for the winner
equals its deficit for the loser; team views differ in which episodes enter.
Verdict for a lost ball, from the loser's ps and pd: positioning if ps < 0.5; reading if
ps >= 0.5 and pd < 0.5; after the anchor otherwise. Immediate: lead under 0.5 s; reported, not
decomposed.
"""

import numpy as np
import pandas as pd

SHARES = ("positioning", "reading", "after the anchor")
IMMEDIATE_LEAD = 0.5  # seconds
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


def decompose(p_static_rel, p_dynamic_rel, releasing_won, lead) -> pd.DataFrame:
    """Per episode: the loser's and winner's probabilities, deficit and credit shares, verdict."""
    ps, pd_ = np.asarray(p_static_rel, float), np.asarray(p_dynamic_rel, float)
    won = np.asarray(releasing_won, bool)
    immediate = np.asarray(lead, float) < IMMEDIATE_LEAD
    ps_loser = np.where(won, 1 - ps, ps)
    pd_loser = np.where(won, 1 - pd_, pd_)
    out = pd.DataFrame(
        {
            "immediate": immediate,
            "loser_side": np.where(won, "other", "releasing"),
            "p_static_loser": ps_loser,
            "p_dynamic_loser": pd_loser,
        }
    )
    d = deficit_shares(ps_loser, pd_loser).add_prefix("deficit ")
    c = credit_shares(1 - ps_loser, 1 - pd_loser).add_prefix("credit ")
    out = pd.concat([out, d, c], axis=1)
    share_cols = [*d.columns, *c.columns]
    out.loc[immediate, share_cols] = np.nan
    out["verdict"] = np.where(immediate, "immediate", verdict(ps_loser, pd_loser))
    return out


def team_shares(table: pd.DataFrame, n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Per team: mean deficit shares over its lost balls and credit shares over its won balls.

    table: one row per non-immediate episode with match_id, losing_team, winning_team and the
    "deficit ..." and "credit ..." columns. Intervals: 2.5 and 97.5 percentiles of a bootstrap
    that resamples episodes with replacement within each match.
    """
    rng = np.random.default_rng(seed)
    teams = sorted(set(table["losing_team"]) | set(table["winning_team"]))
    by_match = [g.index.to_numpy() for _, g in table.groupby("match_id")]

    def means(t: pd.DataFrame) -> dict:
        out = {}
        for team in teams:
            lost, won = t[t["losing_team"] == team], t[t["winning_team"] == team]
            for s in SHARES:
                out[(team, f"deficit {s}")] = lost[f"deficit {s}"].mean()
                out[(team, f"credit {s}")] = won[f"credit {s}"].mean()
        return out

    point = means(table)
    boot = [
        means(table.loc[np.concatenate([rng.choice(ix, len(ix)) for ix in by_match])]) for _ in range(n_boot)
    ]
    boot = pd.DataFrame(boot)
    rows = []
    for team in teams:
        row = {
            "team": team,
            "lost": int((table["losing_team"] == team).sum()),
            "won": int((table["winning_team"] == team).sum()),
        }
        for kind in ("deficit", "credit"):
            for s in SHARES:
                key = (team, f"{kind} {s}")
                row[f"{kind} {s}"] = point[key]
                row[f"{kind} {s} lo"] = boot[key].quantile(0.025)
                row[f"{kind} {s} hi"] = boot[key].quantile(0.975)
        rows.append(row)
    return pd.DataFrame(rows)
