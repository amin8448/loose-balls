"""Timestamp export per verdict for video review (step 2, D8).

One row per decomposed episode: match id, period, clock, frame, team, verdict. The frame is the
anchor frame of the measured leg, the team is the team that lost the ball (the verdict is about
its loss), and the clock is the tracking timestamp of that frame.
"""

from collections.abc import Mapping

import pandas as pd

from looseball import tracking

COLUMNS = ["match_id", "period", "clock", "frame", "team", "verdict"]


def match_clock(match_id: int) -> pd.Series:
    """Tracking timestamp indexed by frame."""
    return tracking.load_frames(match_id).set_index("frame")["timestamp"]


def export_clips(table: pd.DataFrame, clocks: Mapping[int, pd.Series]) -> pd.DataFrame:
    """table: match_id, period, frame, team, verdict. clocks: per match, timestamp by frame."""
    out = table[["match_id", "period", "frame", "team", "verdict"]].copy()
    out["clock"] = [clocks[m].get(f) for m, f in zip(out["match_id"], out["frame"])]
    return out[COLUMNS].sort_values(["match_id", "frame"]).reset_index(drop=True)
