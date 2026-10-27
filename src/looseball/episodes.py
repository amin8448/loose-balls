"""Possession pairs, trigger, resolution and continuity classes, candidate loose-ball episodes.

Definitions follow docs/step1_audit_brief.md (provisional) until they are frozen in DESIGN.md.
Inputs are player_possession boundaries, start_type, end_type, pass_outcome, is_header,
the game_interruption fields and team and player ids. No SkillCorner model output is used.
"""

import numpy as np
import pandas as pd

from looseball import io, paths

RESTART_START_TYPES = (
    "throw_in_reception",
    "free_kick_reception",
    "goal_kick_reception",
    "corner_reception",
    "throw_in_interception",
    "free_kick_interception",
    "goal_kick_interception",
    "corner_interception",
)
LOOSE_TRIGGERS = ("T1", "T2", "T3", "T4", "T5", "T6")
TRIGGER_LABELS = {
    "T0": "T0 normal",
    "T1": "T1 clearance",
    "T2": "T2 failed pass",
    "T3": "T3 shot",
    "T4": "T4 dispossession",
    "T5": "T5 header, non-pass",
    "T6": "T6 unknown",
    "other": "other",
}
RESOLUTIONS = ("pass_reception", "pass_interception", "recovery", "keep_possession", "unknown")
CONTINUITY = ("same player", "same team", "change of team")

POSSESSION_FIELDS = [
    "event_id",
    "index",
    "frame_start",
    "frame_end",
    "period",
    "team_id",
    "player_id",
    "player_position",
    "start_type",
    "end_type",
    "pass_outcome",
    "is_header",
    "game_interruption_before",
    "game_interruption_after",
    "x_start",
    "y_start",
    "attacking_side",
    "fully_extrapolated",
]


def possessions(match_id: int) -> pd.DataFrame:
    """All player_possession rows of a match, sorted by frame_start."""
    ev = io.load_events(match_id)
    pp = ev.loc[ev["event_type"] == "player_possession", POSSESSION_FIELDS]
    return pp.sort_values(["frame_start", "index"], kind="stable").reset_index(drop=True)


def trigger_class(end_type: pd.Series, pass_outcome: pd.Series, is_header: pd.Series) -> pd.Series:
    """Trigger class of possession i. The header rule is tested first (see AUDIT.md, A1 notes)."""
    conditions = [
        is_header.astype(bool) & ~end_type.isin(["pass", "shot"]),
        end_type.eq("clearance"),
        end_type.eq("pass") & pass_outcome.eq("unsuccessful"),
        end_type.eq("shot"),
        end_type.eq("possession_loss"),
        end_type.eq("unknown"),
        end_type.eq("pass") & pass_outcome.eq("successful"),
    ]
    choices = ["T5", "T1", "T2", "T3", "T4", "T6", "T0"]
    return pd.Series(np.select(conditions, choices, default="other"), index=end_type.index)


def pairs(match_id: int) -> pd.DataFrame:
    """Consecutive possession pairs (i, i+1) with drop reasons, classes, gap and candidate flag.

    Columns of possession i carry the suffix _i, those of possession i+1 the suffix _next.
    """
    pp = possessions(match_id)
    a = pp.iloc[:-1].reset_index(drop=True).add_suffix("_i")
    b = pp.iloc[1:].reset_index(drop=True).add_suffix("_next")
    p = pd.concat([a, b], axis=1)
    p.insert(0, "match_id", match_id)
    p.insert(1, "seq_i", np.arange(len(p)))
    p.insert(2, "seq_next", np.arange(1, len(p) + 1))

    p["drop_period"] = p["period_i"] != p["period_next"]
    p["drop_restart"] = p["start_type_next"].isin(RESTART_START_TYPES)
    p["drop_offside"] = p["pass_outcome_i"].eq("offside")
    p["drop_interruption"] = (
        p["game_interruption_after_i"].notna() | p["game_interruption_before_next"].notna()
    )
    p["retained"] = ~(p["drop_period"] | p["drop_restart"] | p["drop_offside"] | p["drop_interruption"])

    p["gap"] = p["frame_start_next"] - p["frame_end_i"]
    p["release_frame"] = p["frame_end_i"]
    p["pickup_frame"] = p["frame_start_next"]
    p["trigger"] = trigger_class(p["end_type_i"], p["pass_outcome_i"], p["is_header_i"])
    p["resolution"] = p["start_type_next"]
    p["continuity"] = np.select(
        [p["player_id_i"] == p["player_id_next"], p["team_id_i"] == p["team_id_next"]],
        ["same player", "same team"],
        default="change of team",
    )
    p["candidate"] = (
        p["retained"]
        & (p["trigger"].isin(LOOSE_TRIGGERS) | p["resolution"].isin(["recovery", "unknown"]))
        & (p["gap"] >= 1)
        & (p["continuity"] != "same player")
    )
    return p


def all_pairs() -> pd.DataFrame:
    return pd.concat([pairs(m) for m in paths.EXPLORATION], ignore_index=True)
