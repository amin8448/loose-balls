"""Camera gate (step 2, D7).

An episode is kept when at least 85% of the players within the radius are detected on the anchor
frame and the winner is detected on the pickup frame. An episode with nobody within the radius
counts as fully observed on the first condition. The radius enters through the race summary the
counts come from. The winner is read here because the gate is defined on it (decided before any
step 2 code, AUDIT.md step 2 setup); nothing is fitted on it.
"""

import numpy as np
import pandas as pd

GATE_SHARE = 0.85


def keep(n_in_race, n_detected, winner_detected, share: float = GATE_SHARE) -> np.ndarray:
    n, k = np.asarray(n_in_race, float), np.asarray(n_detected, float)
    observed = (n == 0) | (k >= share * n)
    return observed & np.asarray(winner_detected, bool)


def drop_rates(table: pd.DataFrame, by: str) -> pd.DataFrame:
    """Episodes, dropped episodes and drop rate for each value of a column, and overall."""
    rows = [
        {by: v, "episodes": len(g), "dropped": int((~g["kept"]).sum()), "drop rate": (~g["kept"]).mean()}
        for v, g in table.groupby(by, sort=True)
    ]
    rows.append({by: "all", "episodes": len(table), "dropped": int((~table["kept"]).sum()),
                 "drop rate": (~table["kept"]).mean()})  # fmt: skip
    return pd.DataFrame(rows)


def win_share_difference(table: pd.DataFrame, n_boot: int = 2000, seed: int = 0) -> dict:
    """Releasing team's win share among dropped and kept episodes, their difference and its interval.

    table: match_id, kept, releasing_won. Interval: 2.5 and 97.5 percentiles of a bootstrap that
    resamples episodes with replacement within each match.
    """
    rng = np.random.default_rng(seed)

    def diff(t):
        return t.loc[~t["kept"], "releasing_won"].mean() - t.loc[t["kept"], "releasing_won"].mean()

    by_match = [g.index.to_numpy() for _, g in table.groupby("match_id")]
    boot = np.array(
        [diff(table.loc[np.concatenate([rng.choice(ix, len(ix)) for ix in by_match])]) for _ in range(n_boot)]
    )
    return {
        "win share dropped": table.loc[~table["kept"], "releasing_won"].mean(),
        "win share kept": table.loc[table["kept"], "releasing_won"].mean(),
        "difference": diff(table),
        "lo": np.nanquantile(boot, 0.025),
        "hi": np.nanquantile(boot, 0.975),
    }
