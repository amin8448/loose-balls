"""Synthetic looseball tables for the public API tests."""

import numpy as np
import pandas as pd

from looseball.schema import CORNERS

FULL_VIEW = [(-60.0, 40.0), (60.0, 40.0), (60.0, -40.0), (-60.0, -40.0)]  # top_left, top_right, ...


def tracking(n_frames: int, ball, players: dict, views=None, period=None) -> pd.DataFrame:
    """ball: (n, 2) array; players: column_id -> (x, y, detected) arrays (NaN x: absent);
    views: list of polygons (4 corner tuples) or None per frame (default: full view)."""
    ball = np.asarray(ball, float)
    t = pd.DataFrame(
        {
            "frame": np.arange(n_frames),
            "period_id": pd.array(period if period is not None else [1] * n_frames, dtype="Int8"),
            "clock": [f"00:00:{f / 10:05.2f}" for f in range(n_frames)],
            "ball_x": ball[:, 0],
            "ball_y": ball[:, 1],
            "ball_z": np.zeros(n_frames),
            "ball_detected": pd.array([True] * n_frames, dtype="boolean"),
        }
    )
    views = views if views is not None else [FULL_VIEW] * n_frames
    for k, c in enumerate(CORNERS):
        t[f"camera_{c}_x"] = [v[k][0] if v is not None else np.nan for v in views]
        t[f"camera_{c}_y"] = [v[k][1] if v is not None else np.nan for v in views]
    for cid, (x, y, det) in players.items():
        t[f"{cid}_x"], t[f"{cid}_y"] = np.asarray(x, float), np.asarray(y, float)
        t[f"{cid}_detected"] = pd.array(np.asarray(det, bool), dtype="boolean")
    return t


def possession(start, end, team, player, start_kind, end_kind, end_result=None, header=False, period=1,
               goalkeeper=False, before=False, after=False) -> dict:  # fmt: skip
    return {
        "match_id": 1,
        "start_frame": start,
        "end_frame": end,
        "period_id": period,
        "team_id": team,
        "player_id": player,
        "goalkeeper": goalkeeper,
        "header": header,
        "start_kind": start_kind,
        "end_kind": end_kind,
        "end_result": end_result,
        "interruption_before": before,
        "interruption_after": after,
    }


def possessions(rows: list[dict]) -> pd.DataFrame:
    p = pd.DataFrame(rows)
    p.insert(1, "event_index", np.arange(len(p)))
    return p


PLAYERS = pd.DataFrame(
    {
        "id": [1, 2, 3, 4],
        "team_id": [10, 20, 10, 20],
        "column_id": ["home_1", "away_2", "home_3", "away_4"],
        "position": ["unspecified", "unspecified", "unspecified", "goalkeeper"],
    }
)


def still(n: int, x: float, y: float, detected: bool = True):
    return np.full(n, x), np.full(n, y), np.full(n, detected)
