"""Timestamp export per verdict for video review (step 2, D8): export_clips."""

from collections.abc import Mapping
from pathlib import Path

import pandas as pd

COLUMNS = ["match_id", "period", "clock", "frame", "team", "verdict"]


def match_clock(tracking: pd.DataFrame) -> pd.Series:
    """The match clock of a tracking table, indexed by frame."""
    return tracking.set_index("frame")["clock"]


def export_clips(
    decomposed: pd.DataFrame,
    episodes: pd.DataFrame,
    clocks: Mapping[int, pd.Series],
    path: str | Path | None = None,
) -> pd.DataFrame:
    """The timestamp table for video review (step 2, D8).

    Inputs: decompose() output; the find_episodes() table(s) of the same episodes (for the
    period and the anchor frame); per match, the match clock by frame (match_clock()).
    Output, one row per decomposed episode, sorted by match and frame: match_id, period,
    clock, frame (the measured anchor frame), team (the team that lost the ball), verdict.
    Written as CSV to `path` when given.
    """
    key = ["match_id", "seq_i"]
    ep = episodes.set_index(key)[["period_id", "anchor_frame"]]
    t = decomposed.join(ep, on=key)
    out = pd.DataFrame(
        {
            "match_id": t["match_id"],
            "period": t["period_id"],
            "frame": t["anchor_frame"],
            "team": t["losing_team"],
            "verdict": t["verdict"],
        }
    )
    out["clock"] = [clocks[m].get(f) for m, f in zip(out["match_id"], out["frame"])]
    out = out[COLUMNS].sort_values(["match_id", "frame"]).reset_index(drop=True)
    if path is not None:
        out.to_csv(path, index=False)
    return out
