"""The SkillCorner adapter on tiny files in the open-data layout."""

import json

import numpy as np
import pandas as pd

from looseball.adapters import skillcorner as sc


def _write_match(root, match_id=7):
    d = root / "data" / "matches" / str(match_id)
    d.mkdir(parents=True)
    meta = {
        "id": match_id,
        "home_team": {"id": 10, "short_name": "Home FC"},
        "away_team": {"id": 20, "short_name": "Away FC"},
        "pitch_length": 104,
        "pitch_width": 68,
        "players": [
            {"id": 1, "team_id": 10, "number": 9, "player_role": {"acronym": "CF"}},
            {"id": 2, "team_id": 20, "number": 1, "player_role": {"acronym": "GK"}},
        ],
    }
    (d / f"{match_id}_match.json").write_text(json.dumps(meta))
    events = pd.DataFrame(
        {
            "event_id": ["1_0", "1_1", "1_2", "1_3"],
            "index": [0, 1, 2, 3],
            "event_type": ["player_possession", "off_ball_run", "player_possession", "player_possession"],
            "frame_start": [1, 1, 5, 9],
            "frame_end": [3, 4, 6, 9],
            "period": [1, 1, 1, 1],
            "team_id": [10, 10, 20, 20],
            "player_id": [1, 1, 2, 2],
            "player_position": ["CF", "CF", "GK", "GK"],
            "is_header": [False, False, True, False],
            "start_type": ["pass_reception", None, "throw_in_reception", "keep_possession"],
            "end_type": ["pass", None, "possession_loss", "pass"],
            "pass_outcome": ["unsuccessful", None, None, "offside"],
            "game_interruption_before": [None, None, "throw_in_for", None],
            "game_interruption_after": [None, None, None, "free_kick_against"],
        }
    )
    events.to_csv(d / f"{match_id}_dynamic_events.csv", index=False)
    corners = {f"{a}_{c}": v for c in ("top_left", "bottom_left", "bottom_right", "top_right")
               for a, v in (("x", 1.0), ("y", 2.0))}  # fmt: skip
    empty = {k: None for k in corners}
    lines = [
        {"frame": 0, "timestamp": None, "period": None, "ball_data": {"x": None, "y": None, "z": None, "is_detected": None},
         "possession": {"player_id": None, "group": None}, "image_corners_projection": empty, "player_data": []},
        {"frame": 1, "timestamp": "00:00:00.00", "period": 1, "ball_data": {"x": 0.5, "y": -0.5, "z": 0.1, "is_detected": True},
         "possession": {"player_id": None, "group": None}, "image_corners_projection": corners,
         "player_data": [{"x": 3.0, "y": 4.0, "player_id": 1, "is_detected": True},
                         {"x": -50.0, "y": 0.0, "player_id": 2, "is_detected": False}]},
        {"frame": 2, "timestamp": "00:00:00.10", "period": 1, "ball_data": {"x": 0.6, "y": -0.4, "z": 0.1, "is_detected": False},
         "possession": {"player_id": None, "group": None}, "image_corners_projection": corners,
         "player_data": [{"x": 3.1, "y": 4.1, "player_id": 1, "is_detected": True}]},
    ]  # fmt: skip
    (d / f"{match_id}_tracking_extrapolated.jsonl").write_text("\n".join(json.dumps(x) for x in lines) + "\n")


def test_adapter_builds_the_looseball_tables(tmp_path):
    _write_match(tmp_path)
    assert sc.match_ids(tmp_path) == [7]
    m = sc.load_match(tmp_path, 7)
    assert m.team_names == {10: "Home FC", 20: "Away FC"} and m.pitch_dimensions == (104.0, 68.0)
    assert list(m.players["column_id"]) == ["home_9", "away_1"]
    assert list(m.players["position"]) == ["unspecified", "goalkeeper"]

    p = m.possessions
    assert len(p) == 3  # the off-ball run is not a possession
    assert list(p["start_kind"]) == ["reception", "restart", "kept"]
    assert list(p["end_kind"]) == ["pass", "loss", "pass"]
    assert list(p["end_result"].fillna("none")) == ["fail", "none", "offside"]
    assert list(p["header"]) == [False, True, False] and list(p["goalkeeper"]) == [False, True, True]
    assert list(p["interruption_before"]) == [False, True, False]
    assert list(p["interruption_after"]) == [False, False, True]

    t = m.tracking
    assert list(t["frame"]) == [0, 1, 2] and list(t["clock"].fillna("")) == ["", "00:00:00.00", "00:00:00.10"]
    assert np.isnan(t.loc[0, "ball_x"]) and t.loc[1, "ball_x"] == 0.5
    assert (
        pd.isna(t.loc[0, "ball_detected"])
        and bool(t.loc[1, "ball_detected"])
        and not bool(t.loc[2, "ball_detected"])
    )
    assert t.loc[1, "camera_top_left_x"] == 1.0 and np.isnan(t.loc[0, "camera_bottom_right_y"])
    assert list(t["home_9_x"].fillna(-1)) == [-1, 3.0, 3.1]
    assert np.isnan(t.loc[2, "away_1_x"]) and not bool(t.loc[1, "away_1_detected"])
