"""Tracking frames and player positions as tables, cached as parquet under data/cache.

Two tables per match:
- frames: one row per frame with period, timestamp, the ball_data fields, the
  image_corners_projection fields and a frame class.
- players: one row per player per frame with x, y and is_detected.

Column names keep the JSON field paths (ball_data.x, image_corners_projection.x_top_left).
The possession field of the tracking is dropped on read; it is not used.

Frame class:
- empty: player_data is empty.
- camera: player_data is present and all eight image_corners_projection values are set.
- no_camera: player_data is present and the image corners are missing.
"""

import json

import numpy as np
import pandas as pd

from looseball import guard

BALL_FIELDS = ("x", "y", "z", "is_detected")
CORNER_FIELDS = (
    "x_top_left",
    "y_top_left",
    "x_bottom_left",
    "y_bottom_left",
    "x_bottom_right",
    "y_bottom_right",
    "x_top_right",
    "y_top_right",
)
FRAME_CLASSES = ("camera", "no_camera", "empty")


def _parse(match_id: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames = {k: [] for k in ("frame", "period", "timestamp", "n_players")}
    frames.update({f"ball_data.{k}": [] for k in BALL_FIELDS})
    frames.update({f"image_corners_projection.{k}": [] for k in CORNER_FIELDS})
    players = {k: [] for k in ("frame", "player_id", "x", "y", "is_detected")}

    with open(guard.match_path(match_id, "tracking")) as f:
        for line in f:
            d = json.loads(line)
            frame = d["frame"]
            frames["frame"].append(frame)
            frames["period"].append(d["period"])
            frames["timestamp"].append(d["timestamp"])
            frames["n_players"].append(len(d["player_data"]))
            ball = d["ball_data"] or {}
            for k in BALL_FIELDS:
                frames[f"ball_data.{k}"].append(ball.get(k))
            corners = d["image_corners_projection"] or {}
            for k in CORNER_FIELDS:
                frames[f"image_corners_projection.{k}"].append(corners.get(k))
            for p in d["player_data"]:
                players["frame"].append(frame)
                players["player_id"].append(p["player_id"])
                players["x"].append(p["x"])
                players["y"].append(p["y"])
                players["is_detected"].append(p["is_detected"])

    fr = pd.DataFrame(frames)
    fr["period"] = fr["period"].astype("Int8")
    for k in ("x", "y", "z"):
        fr[f"ball_data.{k}"] = fr[f"ball_data.{k}"].astype("float64")
    fr["ball_data.is_detected"] = fr["ball_data.is_detected"].astype("boolean")
    corner_cols = [f"image_corners_projection.{k}" for k in CORNER_FIELDS]
    fr[corner_cols] = fr[corner_cols].astype("float64")
    corners_set = fr[corner_cols].notna().all(axis=1)
    fr["frame_class"] = np.where(fr["n_players"] == 0, "empty", np.where(corners_set, "camera", "no_camera"))

    pl = pd.DataFrame(players)
    pl["is_detected"] = pl["is_detected"].astype("boolean")
    return fr, pl


def _cached(match_id: int, name: str) -> pd.DataFrame:
    path = guard.cache_path(match_id, name)
    if not path.exists():
        build_cache(match_id)
    return pd.read_parquet(path)


def build_cache(match_id: int) -> None:
    fr, pl = _parse(match_id)
    for name, table in (("frames", fr), ("players", pl)):
        path = guard.cache_path(match_id, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        table.to_parquet(tmp, index=False)
        tmp.replace(path)


def load_frames(match_id: int) -> pd.DataFrame:
    return _cached(match_id, "frames")


def load_players(match_id: int) -> pd.DataFrame:
    return _cached(match_id, "players")
