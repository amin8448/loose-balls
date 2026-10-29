"""Player velocities from tracking positions (step 2, D4).

Savitzky-Golay first derivative of x and y, window 5 frames, order 2, fixed in advance; window 7
is a stability variant (V3). The filter runs within each track: a run of consecutive frames of
one player. At the ends of a track scipy's "interp" mode fits the polynomial to the first or last
window. A track shorter than the window gets no velocity (NaN). Positions are used as delivered,
detected or extrapolated; is_detected is carried along for flagging.
"""

from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

from looseball_research import paths, tracking

WINDOW = 5
ORDER = 2


def smooth_velocities(players: pd.DataFrame, window: int = WINDOW, order: int = ORDER) -> pd.DataFrame:
    """Players table (frame, player_id, x, y, is_detected) with vx, vy and speed in m/s added."""
    if window % 2 == 0 or window <= order:
        raise ValueError(f"window must be odd and larger than the order, got {window} and {order}")
    p = players.sort_values(["player_id", "frame"], kind="stable").reset_index(drop=True)
    new_track = (p["player_id"] != p["player_id"].shift()) | (p["frame"].diff() != 1)
    track = new_track.cumsum().to_numpy()
    x, y = p["x"].to_numpy(dtype=float), p["y"].to_numpy(dtype=float)
    vx, vy = np.full(len(p), np.nan), np.full(len(p), np.nan)
    starts = np.flatnonzero(np.r_[True, track[1:] != track[:-1]])
    ends = np.r_[starts[1:], len(p)]
    for s, e in zip(starts, ends):
        if e - s < window:
            continue
        kw = {
            "window_length": window,
            "polyorder": order,
            "deriv": 1,
            "delta": 1 / paths.FPS,
            "mode": "interp",
        }
        vx[s:e] = savgol_filter(x[s:e], **kw)
        vy[s:e] = savgol_filter(y[s:e], **kw)
    return p.assign(vx=vx, vy=vy, speed=np.hypot(vx, vy))


@lru_cache(maxsize=10)
def match_velocities(match_id: int, window: int = WINDOW) -> pd.DataFrame:
    """Smoothed velocities for every player-frame of a match, sorted by frame."""
    v = smooth_velocities(tracking.load_players(match_id), window=window)
    return v.sort_values(["frame", "player_id"], kind="stable").reset_index(drop=True)
