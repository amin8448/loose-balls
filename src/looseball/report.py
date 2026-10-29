"""Team-level shares (step 2, D8): team_report.

Per team, over its lost loose balls: the share under each categorical verdict and the mean
continuous deficit shares; over its won loose balls: the mean credit shares. Intervals: 2.5 and
97.5 percentiles of a bootstrap that resamples episodes with replacement within each match.
Team level only; no player values.
"""

import numpy as np
import pandas as pd

from looseball.decompose import SHARES

N_BOOT = 2000
SEED = 0
SMALL_SAMPLE_MATCHES = 2


def bootstrap_within_match(t: pd.DataFrame, stat, n_boot: int = N_BOOT, seed: int = SEED) -> list:
    rng = np.random.default_rng(seed)
    by_match = [g.index.to_numpy() for _, g in t.groupby("match_id")]
    return [stat(t.loc[np.concatenate([rng.choice(ix, len(ix)) for ix in by_match])]) for _ in range(n_boot)]


def verdict_shares(t: pd.DataFrame, n_boot: int = N_BOOT, seed: int = SEED) -> pd.DataFrame:
    """Share of each team's lost balls under each verdict, with intervals."""
    teams = sorted(t["losing_team"].unique())

    def shares(d):
        return {
            (team, v): (d.loc[d["losing_team"] == team, "verdict"] == v).mean()
            for team in teams
            for v in SHARES
        }

    point = shares(t)
    boot = pd.DataFrame(bootstrap_within_match(t, shares, n_boot, seed))
    rows = []
    for team in teams:
        row = {"team": team, "lost": int((t["losing_team"] == team).sum())}
        for v in SHARES:
            row[v] = point[(team, v)]
            row[f"{v} lo"], row[f"{v} hi"] = boot[(team, v)].quantile(0.025), boot[(team, v)].quantile(0.975)
        rows.append(row)
    return pd.DataFrame(rows)


def continuous_shares(table: pd.DataFrame, n_boot: int = N_BOOT, seed: int = SEED) -> pd.DataFrame:
    """Mean deficit shares over each team's lost balls and credit shares over its won balls."""
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
    boot = pd.DataFrame(
        [
            means(table.loc[np.concatenate([rng.choice(ix, len(ix)) for ix in by_match])])
            for _ in range(n_boot)
        ]
    )
    rows = []
    for team in teams:
        row = {"team": team, "lost": int((table["losing_team"] == team).sum()),
               "won": int((table["winning_team"] == team).sum())}  # fmt: skip
        for kind in ("deficit", "credit"):
            for s in SHARES:
                key = (team, f"{kind} {s}")
                row[f"{kind} {s}"] = point[key]
                row[f"{kind} {s} lo"] = boot[key].quantile(0.025)
                row[f"{kind} {s} hi"] = boot[key].quantile(0.975)
        rows.append(row)
    return pd.DataFrame(rows)


def team_report(
    decomposed: pd.DataFrame,
    n_boot: int = N_BOOT,
    seed: int = SEED,
    team_names: dict | None = None,
    matches_per_team: dict | None = None,
) -> dict:
    """Team-level shares with bootstrap intervals (step 2, D8).

    Input: decompose() output for the episodes to report (immediate episodes are left out), in a
    fixed row order. Output: {"verdicts": ..., "shares": ..., "seed": seed, "replicates": n_boot}.
    "verdicts" has, per losing team, the share of its lost balls under each verdict with
    intervals; "shares" has the mean deficit shares over lost balls and credit shares over won
    balls with intervals. Both carry the team's name, its number of matches and a small-sample
    flag (2 matches or fewer). Intervals resample episodes within match.
    """
    t = decomposed[decomposed["verdict"] != "immediate"].reset_index(drop=True)
    if matches_per_team is None:
        matches_per_team = {}
        for team in set(t["losing_team"]) | set(t["winning_team"]):
            matches_per_team[team] = t.loc[
                (t["losing_team"] == team) | (t["winning_team"] == team), "match_id"
            ].nunique()
    names = team_names or {}
    cols = [
        "match_id",
        "losing_team",
        "winning_team",
        *[f"{k} {s}" for k in ("deficit", "credit") for s in SHARES],
    ]
    verdicts = verdict_shares(t, n_boot, seed)
    shares = continuous_shares(t[cols], n_boot, seed)
    for table in (verdicts, shares):
        table.insert(1, "name", table["team"].map(names))
        table.insert(2, "matches", table["team"].map(matches_per_team))
        table.insert(3, "small sample", table["matches"] <= SMALL_SAMPLE_MATCHES)
    return {"verdicts": verdicts, "shares": shares, "seed": seed, "replicates": n_boot}
