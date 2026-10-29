"""Adapter: SkillCorner open data to the looseball tables (looseball.schema).

Reads one match of the SkillCorner open-data repository (github.com/SkillCorner/opendata):
<data>/data/matches/<id>/<id>_match.json, <id>_dynamic_events.csv and
<id>_tracking_extrapolated.jsonl. This is the only module of looseball that names SkillCorner
fields. Only possession boundaries and types, interruption marks, positions, detection flags and
the camera polygon are read: no SkillCorner model output, and not the tracking possession field.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from looseball.adapters import Match
from looseball.schema import CORNERS

RESTARTS = ("throw_in", "free_kick", "goal_kick", "corner")
START_KIND = {
    "pass_reception": "reception",
    "pass_interception": "interception",
    "recovery": "recovery",
    "keep_possession": "kept",
    "unknown": "unknown",
    **{f"{r}_{k}": "restart" for r in RESTARTS for k in ("reception", "interception")},
}
END_KIND = {
    "pass": "pass",
    "shot": "shot",
    "clearance": "clearance",
    "possession_loss": "loss",
    "foul_suffered": "foul",
    "unknown": "unknown",
}
END_RESULT = {"successful": "success", "unsuccessful": "fail", "offside": "offside"}


def _file(data, match_id: int, suffix: str) -> Path:
    return Path(data) / "data" / "matches" / str(match_id) / f"{match_id}{suffix}"


def match_ids(data) -> list[int]:
    """Match ids present in the open-data clone at `data`."""
    return sorted(int(p.name) for p in (Path(data) / "data" / "matches").iterdir() if p.is_dir())


def _players(meta: dict) -> pd.DataFrame:
    home = meta["home_team"]["id"]
    rows = [
        {
            "id": p["id"],
            "team_id": p["team_id"],
            "column_id": f"{'home' if p['team_id'] == home else 'away'}_{p['number']}",
            "position": "goalkeeper" if p["player_role"]["acronym"] == "GK" else "unspecified",
        }
        for p in meta["players"]
    ]
    players = pd.DataFrame(rows)
    if players["column_id"].duplicated().any():
        raise ValueError("two players of one team share a shirt number")
    return players


def _possessions(events: pd.DataFrame, match_id: int) -> pd.DataFrame:
    pp = events[events["event_type"] == "player_possession"]
    return pd.DataFrame(
        {
            "match_id": match_id,
            "original_event_id": pp["event_id"].to_numpy(),
            "event_index": pp["index"].to_numpy(),
            "start_frame": pp["frame_start"].to_numpy(),
            "end_frame": pp["frame_end"].to_numpy(),
            "period_id": pp["period"].to_numpy(),
            "team_id": pp["team_id"].to_numpy(),
            "player_id": pp["player_id"].to_numpy(),
            "goalkeeper": pp["player_position"].eq("GK").to_numpy(),
            "header": pp["is_header"].astype(bool).to_numpy(),
            "start_kind": pp["start_type"].map(START_KIND).to_numpy(),
            "end_kind": pp["end_type"].map(END_KIND).to_numpy(),
            "end_result": pp["pass_outcome"].map(END_RESULT).to_numpy(),
            "interruption_before": pp["game_interruption_before"].notna().to_numpy(),
            "interruption_after": pp["game_interruption_after"].notna().to_numpy(),
        }
    )


def _tracking(path: Path, players: pd.DataFrame) -> pd.DataFrame:
    frames = {
        "frame": [],
        "period_id": [],
        "clock": [],
        "ball_x": [],
        "ball_y": [],
        "ball_z": [],
        "ball_detected": [],
    }
    frames.update({f"camera_{c}_{a}": [] for c in CORNERS for a in ("x", "y")})
    long = {"frame": [], "player_id": [], "x": [], "y": [], "detected": []}
    with open(path) as f:
        for line in f:
            d = json.loads(line)
            frame = d["frame"]
            frames["frame"].append(frame)
            frames["period_id"].append(d["period"])
            frames["clock"].append(d["timestamp"])
            ball = d["ball_data"] or {}
            for k in ("x", "y", "z"):
                frames[f"ball_{k}"].append(ball.get(k))
            frames["ball_detected"].append(ball.get("is_detected"))
            view = d["image_corners_projection"] or {}
            for c in CORNERS:
                frames[f"camera_{c}_x"].append(view.get(f"x_{c}"))
                frames[f"camera_{c}_y"].append(view.get(f"y_{c}"))
            for p in d["player_data"]:
                long["frame"].append(frame)
                long["player_id"].append(p["player_id"])
                long["x"].append(p["x"])
                long["y"].append(p["y"])
                long["detected"].append(p["is_detected"])

    tr = pd.DataFrame(frames)
    tr["period_id"] = tr["period_id"].astype("Int8")
    for c in tr.columns:
        if c.startswith(("ball_", "camera_")) and c != "ball_detected":
            tr[c] = tr[c].astype("float64")
    tr["ball_detected"] = tr["ball_detected"].astype("boolean")

    pl = pd.DataFrame(long)
    column_of = players.set_index("id")["column_id"]
    pl["column_id"] = column_of.reindex(pl["player_id"]).to_numpy()
    unknown = pl["column_id"].isna()
    pl.loc[unknown, "column_id"] = "unknown_" + pl.loc[unknown, "player_id"].astype(str)
    pl["x"], pl["y"] = pl["x"].astype("float64"), pl["y"].astype("float64")
    pl["detected"] = pl["detected"].astype("boolean")
    blocks = []
    for cid, g in pl.groupby("column_id", sort=True):
        g = g.set_index("frame")
        blocks.append(
            pd.DataFrame({f"{cid}_x": g["x"], f"{cid}_y": g["y"], f"{cid}_detected": g["detected"]}).reindex(
                tr["frame"]
            )
        )
    wide = pd.concat(blocks, axis=1).reset_index(drop=True) if blocks else pd.DataFrame(index=tr.index)
    for c in wide.columns:
        if c.endswith("_detected"):
            wide[c] = wide[c].astype("boolean")
    out = pd.concat([tr, wide], axis=1)
    if not (out["frame"].to_numpy() == np.arange(len(out))).all():
        raise ValueError("tracking frames are not consecutive from 0")
    return out


def load_match(data, match_id: int) -> Match:
    """One match of the SkillCorner open data as looseball tables."""
    meta = json.loads(_file(data, match_id, "_match.json").read_text())
    players = _players(meta)
    events = pd.read_csv(_file(data, match_id, "_dynamic_events.csv"), low_memory=False)
    return Match(
        match_id=int(match_id),
        tracking=_tracking(_file(data, match_id, "_tracking_extrapolated.jsonl"), players),
        possessions=_possessions(events, int(match_id)),
        players=players,
        home_team_id=meta["home_team"]["id"],
        away_team_id=meta["away_team"]["id"],
        team_names={meta[s]["id"]: meta[s]["short_name"] for s in ("home_team", "away_team")},
        pitch_dimensions=(float(meta["pitch_length"]), float(meta["pitch_width"])),
    )
