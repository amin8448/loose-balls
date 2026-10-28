"""Possession pairs, trigger, resolution and continuity classes, candidate loose-ball episodes.

Definitions follow docs/step1_audit_brief.md with the post hoc revisions logged in AUDIT.md
(step 1, after A1) until they are frozen in DESIGN.md. Inputs are player_possession
boundaries, start_type, end_type, pass_outcome, is_header, the game_interruption fields,
player_position, team and player ids, and tracking positions, detection flags and the camera
polygon (image_corners_projection).
No SkillCorner model output is used.
"""

import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath

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
CONTACT_ANGLE_DEG = 30.0
CONTACT_SPEED_CHANGE = 3.0  # m/s
CONTACT_PLAYER_RADIUS = 1.5  # metres
CONTACT_EDGE = 2  # frames; contacts are tested from release + 2 to pickup - 2 (revision 3)
VIEW_CORNERS = ("top_left", "top_right", "bottom_right", "bottom_left")

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


def _in_view(corners: np.ndarray, x: float, y: float) -> bool:
    """corners: (4, 2) in the order of VIEW_CORNERS. A frame without all corners is not in view."""
    if np.isnan(corners).any() or np.isnan(x) or np.isnan(y):
        return False
    return bool(MplPath(corners).contains_point((x, y)))


def ball_kinematics(
    bx: np.ndarray, by: np.ndarray, t: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Horizontal speed into and out of frames t, and the direction change at t in degrees.

    Velocity from consecutive frames (t-1 to t, t to t+1), no smoothing. When either speed is
    zero the direction is undefined and the change is set to 0.
    """
    vin = np.stack([bx[t] - bx[t - 1], by[t] - by[t - 1]], axis=1) * paths.FPS
    vout = np.stack([bx[t + 1] - bx[t], by[t + 1] - by[t]], axis=1) * paths.FPS
    s_in, s_out = np.hypot(*vin.T), np.hypot(*vout.T)
    moving = (s_in > 0) & (s_out > 0)
    cos = np.where(moving, (vin * vout).sum(axis=1) / np.where(moving, s_in * s_out, 1.0), 1.0)
    angle = np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))
    return s_in, s_out, angle


def contact_domain(release: int, pickup: int) -> np.ndarray:
    """Frames at which a contact can be found: release + CONTACT_EDGE to pickup - CONTACT_EDGE."""
    return np.arange(release + CONTACT_EDGE, pickup - CONTACT_EDGE + 1)


def window_structure(p: pd.DataFrame, match_id: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Contacts, legs, anchors, apex and path length for the pairs of one match, and the A9 table.

    Contact (revision 3): a frame t in contact_domain (release+2 to pickup-2), with the ball
    detected on t-1, t and t+1, where the horizontal ball velocity turns by more than
    CONTACT_ANGLE_DEG or its speed changes by more than CONTACT_SPEED_CHANGE, and some player
    (detected or not) is within CONTACT_PLAYER_RADIUS of the ball on t. Consecutive contact
    frames are one contact, placed at the first frame of the run. Legs: the window split at
    its contacts. Anchor of a
    leg: the first frame from the leg start to the leg end (inclusive) at which the pickup point
    lies inside the camera polygon; None if there is no such frame.
    """
    fr = tracking.load_frames(match_id)
    assert (fr["frame"].to_numpy() == np.arange(len(fr))).all()
    pl_frames, pl = _frame_lookup(tracking.load_players(match_id))
    bx = fr["ball_data.x"].to_numpy()
    by = fr["ball_data.y"].to_numpy()
    bz = fr["ball_data.z"].to_numpy()
    bdet = fr["ball_data.is_detected"].fillna(False).to_numpy(dtype=bool)
    corners = np.stack(
        [
            fr[[f"image_corners_projection.x_{c}", f"image_corners_projection.y_{c}"]].to_numpy()
            for c in VIEW_CORNERS
        ],
        axis=1,
    )

    def near(f: int, x: float, y: float, radius: float) -> tuple[np.ndarray, slice]:
        lo, hi = np.searchsorted(pl_frames, [f, f + 1])
        return np.hypot(pl["x"][lo:hi] - x, pl["y"][lo:hi] - y) <= radius, slice(lo, hi)

    rows, checks = [], []
    for idx, r in zip(p.index, p.itertuples(index=False)):
        rel, pk = int(r.release_frame), int(r.pickup_frame)
        px, py = bx[pk], by[pk]

        t = contact_domain(rel, pk)
        evaluable = t[bdet[t - 1] & bdet[t] & bdet[t + 1]]
        s_in, s_out, angle = ball_kinematics(bx, by, evaluable)
        changed = (angle > CONTACT_ANGLE_DEG) | (np.abs(s_out - s_in) > CONTACT_SPEED_CHANGE)
        flagged = [
            int(f) for f in evaluable[changed] if near(f, bx[f], by[f], CONTACT_PLAYER_RADIUS)[0].any()
        ]
        contacts = [f for i, f in enumerate(flagged) if i == 0 or f - flagged[i - 1] > 1]

        view = np.array([_in_view(corners[f], px, py) for f in range(rel, pk + 1)])

        def anchor(start: int, end: int, view=view, rel=rel):
            hits = np.flatnonzero(view[start - rel : end - rel + 1])
            return start + int(hits[0]) if len(hits) else None

        leg1 = (rel, contacts[0] if contacts else pk)
        leg2 = (contacts[-1] if contacts else rel, pk)
        a1, a2 = anchor(*leg1), anchor(*leg2)

        w = np.arange(rel + 1, pk + 1)
        wd = w[bdet[w]]
        apex = int(wd[np.argmax(bz[wd])]) if len(wd) else None
        apex_observed = (
            apex is not None
            and apex + 1 <= pk
            and bdet[apex - 1]
            and bdet[apex + 1]
            and bz[apex - 1] <= bz[apex]
            and bz[apex + 1] <= bz[apex]
        )
        seg = np.hypot(np.diff(bx[rel : pk + 1]), np.diff(by[rel : pk + 1]))

        out = {
            "n_contacts": len(contacts),
            "n_legs": len(contacts) + 1,
            "contact_frames": ";".join(map(str, contacts)),
            "contact_domain_frames": len(t),
            "contact_evaluable_frames": len(evaluable),
            "leg1_start": leg1[0],
            "leg1_end": leg1[1],
            "leg2_start": leg2[0],
            "leg2_end": leg2[1],
            "anchor1_frame": a1,
            "anchor2_frame": a2,
            "lead1_s": (pk - a1) / paths.FPS if a1 is not None else np.nan,
            "lead2_s": (pk - a2) / paths.FPS if a2 is not None else np.nan,
            "apex_frame": apex,
            "apex_observed": bool(apex_observed),
            "apex_to_pickup_s": (pk - apex) / paths.FPS if apex is not None else np.nan,
            "path_length_m": np.nansum(seg),
            "path_missing_segments": int(np.isnan(seg).sum()),
        }
        for name, a in (("anchor1", a1), ("anchor2", a2)):
            for radius in RADII:
                if a is None:
                    out[f"{name}_n{radius}"] = out[f"{name}_det{radius}"] = np.nan
                else:
                    m, sl = near(a, px, py, radius)
                    out[f"{name}_n{radius}"] = int(m.sum())
                    out[f"{name}_det{radius}"] = int((m & pl["is_detected"][sl]).sum())
        rows.append(out)

        if a2 is None:
            continue
        m, sl = near(a2, px, py, 15)
        lo_r, hi_r = np.searchsorted(pl_frames, [rel, rel + 1])
        rel_ids = pl["player_id"][lo_r:hi_r]
        lo_w, hi_w = np.searchsorted(pl_frames, [rel + 1, pk + 1])
        for pid in pl["player_id"][sl][m]:
            at_rel = np.flatnonzero(rel_ids == pid)
            base = {"match_id": match_id, "seq_i": r.seq_i, "trigger": r.trigger, "player_id": pid}
            if not len(at_rel):
                checks.append({**base, "status": "absent at release"})
                continue
            k = lo_r + at_rel[0]
            if pl["is_detected"][k]:
                continue
            later = np.flatnonzero((pl["player_id"][lo_w:hi_w] == pid) & pl["is_detected"][lo_w:hi_w])
            if not len(later):
                checks.append({**base, "status": "not detected by the pickup frame"})
                continue
            j = lo_w + later[0]
            dt = (pl_frames[j] - rel) / paths.FPS
            dist = np.hypot(pl["x"][j] - pl["x"][k], pl["y"][j] - pl["y"][k])
            checks.append({**base, "status": "measured", "seconds": dt, "metres": dist, "speed": dist / dt})
    return pd.DataFrame(rows, index=p.index), pd.DataFrame(checks)


def match_episodes(match_id: int) -> pd.DataFrame:
    """Candidate pairs (gap >= 1) of one match with tracking measures, window structure and scramble ids."""
    p = pairs(match_id)
    sc = scrambles(p)[["scramble_id", "scramble_link", "scramble_links", "scramble_winner_team"]]
    c = p[p["candidate"]].copy()
    c = c.join(window_measures(c, match_id)).join(window_structure(c, match_id)[0]).join(sc)
    return c


def extrapolation_checks(match_id: int) -> pd.DataFrame:
    """A9 rows for the main pairs of one match."""
    p = pairs(match_id)
    return window_structure(p[p["main"]], match_id)[1]


def all_pairs() -> pd.DataFrame:
    return pd.concat([pairs(m) for m in paths.EXPLORATION], ignore_index=True)


def all_episodes() -> pd.DataFrame:
    return pd.concat([match_episodes(m) for m in paths.EXPLORATION], ignore_index=True)


def all_extrapolation_checks() -> pd.DataFrame:
    return pd.concat([extrapolation_checks(m) for m in paths.EXPLORATION], ignore_index=True)
