"""Possession pairs, trigger, resolution and continuity classes, candidate loose-ball episodes.

Definitions follow docs/step1_audit_brief.md with the post hoc revisions logged in AUDIT.md
(step 1, after A1) until they are frozen in DESIGN.md. Inputs are player_possession
boundaries, start_type, end_type, pass_outcome, is_header, the game_interruption fields,
player_position, team and player ids, and tracking positions and detection flags.
No SkillCorner model output is used.
"""

import numpy as np
import pandas as pd

from looseball import io, paths, tracking

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
TRIGGERS = ("T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7")
LOOSE_TRIGGERS = ("T1", "T2", "T3", "T4", "T5", "T6", "T7")
TRIGGER_LABELS = {
    "T0": "T0 normal",
    "T1": "T1 clearance",
    "T2": "T2 failed pass",
    "T3": "T3 shot",
    "T4": "T4 dispossession",
    "T5": "T5 header, non-pass",
    "T6": "T6 unknown",
    "T7": "T7 completed pass, not controlled",
}
RESOLUTIONS = ("pass_reception", "pass_interception", "recovery", "keep_possession", "unknown")
CANDIDATE_RESOLUTIONS = ("recovery", "keep_possession")
CONTINUITY = ("same player", "same team", "change of team")

MIN_GAP = 3  # frames; the main candidate set for A2 to A6, G1, G3 and G4
SCRAMBLE_MAX_FRAMES = 5  # a winning possession shorter than this can link a scramble
SCRAMBLE_END_TYPES = ("possession_loss", "clearance", "unknown")
AERIAL_Z = 1.8  # metres
RADII = (10, 15)  # metres

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


def trigger_class(
    end_type: pd.Series, pass_outcome: pd.Series, is_header: pd.Series, start_type_next: pd.Series
) -> pd.Series:
    """Trigger class of a pair, from possession i (and, for T7, the start_type of i+1).

    The header rule is tested first (see AUDIT.md, A1 implementation choices).
    """
    completed = end_type.eq("pass") & pass_outcome.eq("successful")
    conditions = [
        is_header.astype(bool) & ~end_type.isin(["pass", "shot"]),
        end_type.eq("clearance"),
        end_type.eq("pass") & pass_outcome.eq("unsuccessful"),
        end_type.eq("shot"),
        end_type.eq("possession_loss"),
        end_type.eq("unknown"),
        completed & start_type_next.isin(CANDIDATE_RESOLUTIONS),
        completed,
    ]
    choices = ["T5", "T1", "T2", "T3", "T4", "T6", "T7", "T0"]
    return pd.Series(np.select(conditions, choices, default="other"), index=end_type.index)


def pairs(match_id: int) -> pd.DataFrame:
    """Consecutive possession pairs (i, i+1) with drop reasons, classes, gap and candidate flags.

    Columns of possession i carry the suffix _i, those of possession i+1 the suffix _next.
    candidate: the revised definition with gap >= 1 (the G2 set). main: candidate with
    gap >= MIN_GAP (the set for A2 to A6, G1, G3, G4).
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
    p["drop_foul"] = p["end_type_i"].eq("foul_suffered")
    p["retained"] = ~(
        p["drop_period"] | p["drop_restart"] | p["drop_offside"] | p["drop_interruption"] | p["drop_foul"]
    )

    p["gap"] = p["frame_start_next"] - p["frame_end_i"]
    p["release_frame"] = p["frame_end_i"]
    p["pickup_frame"] = p["frame_start_next"]
    p["trigger"] = trigger_class(p["end_type_i"], p["pass_outcome_i"], p["is_header_i"], p["start_type_next"])
    p["resolution"] = p["start_type_next"]
    p["continuity"] = np.select(
        [p["player_id_i"] == p["player_id_next"], p["team_id_i"] == p["team_id_next"]],
        ["same player", "same team"],
        default="change of team",
    )
    p["gk_save"] = p["trigger"].eq("T3") & p["player_position_next"].eq("GK")
    p["candidate"] = (
        p["retained"]
        & p["trigger"].isin(LOOSE_TRIGGERS)
        & p["resolution"].isin(CANDIDATE_RESOLUTIONS)
        & ~p["gk_save"]
        & (p["continuity"] != "same player")
        & (p["gap"] >= 1)
    )
    p["main"] = p["candidate"] & (p["gap"] >= MIN_GAP)
    return p


def scrambles(p: pd.DataFrame) -> pd.DataFrame:
    """Merge consecutive main pairs of one match into scrambles.

    Main pair k links to the main pair that starts with its winning possession when that
    possession lasts fewer than SCRAMBLE_MAX_FRAMES frames and ends in possession_loss,
    clearance or unknown. Returns the main pairs with scramble_id, scramble_link (position in
    the scramble, from 1), scramble_links (size) and scramble_winner_team.
    """
    m = p[p["main"]].sort_values("seq_i").copy()
    short = (m["frame_end_next"] - m["frame_start_next"]) < SCRAMBLE_MAX_FRAMES
    ends_loose = m["end_type_next"].isin(SCRAMBLE_END_TYPES)
    next_is_main = m["seq_next"].isin(set(m["seq_i"]))
    links_forward = short & ends_loose & next_is_main
    # The pair a main pair links to is the next main pair in sequence order.
    starts_new = ~links_forward.shift(1, fill_value=False)
    m["scramble_id"] = starts_new.cumsum().astype(int) - 1
    m["scramble_link"] = m.groupby("scramble_id").cumcount() + 1
    m["scramble_links"] = m.groupby("scramble_id")["seq_i"].transform("size")
    m["scramble_winner_team"] = m.groupby("scramble_id")["team_id_next"].transform("last")
    return m


def _frame_lookup(players: pd.DataFrame) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    pl = players.sort_values("frame", kind="stable")
    cols = {c: pl[c].to_numpy() for c in ("player_id", "x", "y")}
    cols["is_detected"] = pl["is_detected"].fillna(False).to_numpy(dtype=bool)
    return pl["frame"].to_numpy(), cols


def window_measures(p: pd.DataFrame, match_id: int) -> pd.DataFrame:
    """Tracking measures for the candidate pairs of one match (positions and detection flags only).

    Window: frames strictly after the release frame up to and including the pickup frame.
    Pickup point: tracking ball (ball_data.x, ball_data.y) on the pickup frame.
    """
    fr = tracking.load_frames(match_id)
    assert (fr["frame"].to_numpy() == np.arange(len(fr))).all()
    team_of = io.load_roster(match_id).set_index("id")["team_id"]
    pl_frames, pl = _frame_lookup(tracking.load_players(match_id))
    pl_team = team_of.reindex(pl["player_id"]).to_numpy()

    bx = fr["ball_data.x"].to_numpy()
    by = fr["ball_data.y"].to_numpy()
    bz = fr["ball_data.z"].to_numpy()
    bdet = fr["ball_data.is_detected"].fillna(False).to_numpy(dtype=bool)
    fclass = fr["frame_class"].to_numpy()

    rows = []
    for r in p.itertuples(index=False):
        rel, pk = int(r.release_frame), int(r.pickup_frame)
        w = slice(rel + 1, pk + 1)
        det = bdet[w]
        z_det = bz[w][det]
        px, py = bx[pk], by[pk]
        sign = -1.0 if r.attacking_side_next == "right_to_left" else 1.0
        ex, ey = sign * r.x_start_next, sign * r.y_start_next
        out = {
            "release_frame_class": fclass[rel],
            "pickup_frame_class": fclass[pk],
            "window_frames": pk - rel,
            "window_ball_detected": int(det.sum()),
            "window_no_camera": int((fclass[w] == "no_camera").sum()),
            "window_empty": int((fclass[w] == "empty").sum()),
            "max_ball_z_detected": z_det.max() if len(z_det) else np.nan,
            "pickup_x": px,
            "pickup_y": py,
            "pickup_event_x": ex,
            "pickup_event_y": ey,
            "pickup_disagreement_m": np.hypot(px - ex, py - ey),
            "pickup_disagreement_xmirror_m": np.hypot(px - sign * r.x_start_next, py - r.y_start_next),
            "pickup_disagreement_norotation_m": np.hypot(px - r.x_start_next, py - r.y_start_next),
            "ball_displacement_m": np.hypot(bx[pk] - bx[rel], by[pk] - by[rel]),
        }
        for label, f in (("release", rel), ("pickup", pk)):
            lo, hi = np.searchsorted(pl_frames, [f, f + 1])
            d = np.hypot(pl["x"][lo:hi] - px, pl["y"][lo:hi] - py)
            dt = pl["is_detected"][lo:hi]
            releasing = pl_team[lo:hi] == r.team_id_i
            for radius in RADII:
                near = d <= radius
                for side, mask in (("releasing", releasing), ("other", ~releasing)):
                    out[f"{label}_n{radius}_{side}"] = int((near & mask).sum())
                    out[f"{label}_det{radius}_{side}"] = int((near & mask & dt).sum())
            if label == "pickup":
                winner = pl["player_id"][lo:hi] == r.player_id_next
                out["winner_detected_pickup"] = bool((winner & dt).any())
        rows.append(out)
    m = pd.DataFrame(rows, index=p.index)
    m["aerial"] = m["max_ball_z_detected"] > AERIAL_Z
    m["window_camera_loss"] = (m["window_no_camera"] + m["window_empty"]) > 0
    return m


def match_episodes(match_id: int) -> pd.DataFrame:
    """Candidate pairs (gap >= 1) of one match with tracking measures and scramble ids for main pairs."""
    p = pairs(match_id)
    sc = scrambles(p)[["scramble_id", "scramble_link", "scramble_links", "scramble_winner_team"]]
    c = p[p["candidate"]].copy()
    c = c.join(window_measures(c, match_id)).join(sc)
    return c


def all_pairs() -> pd.DataFrame:
    return pd.concat([pairs(m) for m in paths.EXPLORATION], ignore_index=True)


def all_episodes() -> pd.DataFrame:
    return pd.concat([match_episodes(m) for m in paths.EXPLORATION], ignore_index=True)
