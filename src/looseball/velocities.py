"""Player velocities from tracking positions (step 2, D4): Savitzky-Golay first derivative of x
and y within each track (a run of consecutive frames of one player), window 5 and order 2 by
default; scipy's "interp" mode at track ends; a track shorter than the window gets no velocity.
"""

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

from looseball.episodes import long_players
from looseball.schema import FPS

WINDOW = 5
ORDER = 2


def smooth_velocities(players: pd.DataFrame, window: int = WINDOW, order: int = ORDER) -> pd.DataFrame:
    """Player rows (frame, column_id, x, y, ...) with vx, vy and speed in m/s added."""
    if window % 2 == 0 or window <= order:
        raise ValueError(f"window must be odd and larger than the order, got {window} and {order}")
    p = players.sort_values(["column_id", "frame"], kind="stable").reset_index(drop=True)
    new_track = (p["column_id"] != p["column_id"].shift()) | (p["frame"].diff() != 1)
    track = new_track.cumsum().to_numpy()
    x, y = p["x"].to_numpy(dtype=float), p["y"].to_numpy(dtype=float)
    vx, vy = np.full(len(p), np.nan), np.full(len(p), np.nan)
    starts = np.flatnonzero(np.r_[True, track[1:] != track[:-1]]) if len(p) else np.array([], int)
    ends = np.r_[starts[1:], len(p)]
    kw = {"window_length": window, "polyorder": order, "deriv": 1, "delta": 1 / FPS, "mode": "interp"}
    for s, e in zip(starts, ends):
        if e - s >= window:
            vx[s:e] = savgol_filter(x[s:e], **kw)
            vy[s:e] = savgol_filter(y[s:e], **kw)
    return p.assign(vx=vx, vy=vy, speed=np.hypot(vx, vy))


def tracking_velocities(tracking: pd.DataFrame, window: int = WINDOW) -> pd.DataFrame:
    """Smoothed velocities for every player-frame of a tracking table, sorted by frame."""
    v = smooth_velocities(long_players(tracking), window=window)
    return v.sort_values(["frame", "column_id"], kind="stable").reset_index(drop=True)
