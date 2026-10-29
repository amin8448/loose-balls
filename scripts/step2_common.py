"""Shared table builder for S3, S4 and S5 (exploration matches only).

episode_table(**settings) runs the race for every anchored main pair under the given race
settings and adds the D7 flag, the immediate flag and the outcome column releasing_won (the
team of possession i+1 is the releasing team). Only S3, S4 and S5 read releasing_won.
"""

import json
from functools import lru_cache

import numpy as np
import pandas as pd

from looseball import decompose, episodes, expectation, gate, paths, race

FROZEN = paths.AUDIT_DIR / "frozen_parameters.json"
EPISODE_COLUMNS = [
    "match_id", "seq_i", "trigger", "period_i", "release_frame", "pickup_frame", "pickup_x", "pickup_y",
    "team_id_i", "team_id_next", "player_id_i", "player_id_next", "winner_detected_pickup", "aerial",
    "n_legs", "lead2_s",
]  # fmt: skip


@lru_cache(maxsize=1)
def anchored_pairs() -> pd.DataFrame:
    ep = episodes.all_episodes()
    return ep[ep["main"] & ep["anchor2_frame"].notna()].reset_index(drop=True)


def episode_table(keys: pd.DataFrame | None = None, **settings) -> pd.DataFrame:
    """Race summary per anchored main pair (or per pair in keys: match_id, seq_i) with flags."""
    main = anchored_pairs()
    if keys is not None:
        main = main.merge(keys[["match_id", "seq_i"]], on=["match_id", "seq_i"])
    parts = [race.episode_races(m, d, **settings)[0] for m, d in main.groupby("match_id")]
    t = pd.concat(parts, ignore_index=True).merge(
        main[EPISODE_COLUMNS], on=["match_id", "seq_i"], validate="1:1"
    )
    t["kept"] = gate.keep(
        t["n_releasing"] + t["n_other"],
        t["n_detected_releasing"] + t["n_detected_other"],
        t["winner_detected_pickup"],
    )
    t["immediate"] = t["lead_s"] < decompose.IMMEDIATE_LEAD
    t["releasing_won"] = (t["team_id_next"] == t["team_id_i"]).astype(int)
    return t


def analysis_set(t: pd.DataFrame) -> pd.DataFrame:
    return t[t["kept"] & ~t["immediate"]].reset_index(drop=True)


def save_frozen(params: dict) -> None:
    FROZEN.write_text(json.dumps(params, indent=2) + "\n")


def load_frozen() -> dict:
    return json.loads(FROZEN.read_text())


def probabilities(t: pd.DataFrame, frozen: dict, model_key: str = "chosen") -> pd.DataFrame:
    """p_static and p_dynamic of the releasing team from a frozen entry, and the baselines."""
    a, b = frozen[model_key]["a"], frozen[model_key]["b"]
    out = pd.DataFrame(index=t.index)
    out["p_static"] = expectation.predict((a, b), expectation.features(t, "static")["dt"])
    out["p_dynamic"] = expectation.predict((a, b), expectation.features(t, "dynamic")["dt"])
    f = expectation.features(t, "dynamic")
    for name, col in (("B0", "dn"), ("B1", "dd")):
        out[f"p_{name}"] = expectation.predict((frozen[name]["a"], frozen[name]["b"]), f[col])
    return out


def bootstrap_within_match(t: pd.DataFrame, stat, n_boot: int = 2000, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    by_match = [g.index.to_numpy() for _, g in t.groupby("match_id")]
    return np.array(
        [stat(t.loc[np.concatenate([rng.choice(ix, len(ix)) for ix in by_match])]) for _ in range(n_boot)]
    )
