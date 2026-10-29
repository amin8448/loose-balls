"""Loose-ball episodes: find_episodes (DESIGN.md, step 1 definition with revision 3, and the
step 2 flags: lead, immediate class, camera gate D7).

Inputs are the provider-neutral tables of looseball.schema.
"""

import numpy as np
import pandas as pd
from matplotlib.path import Path as MplPath

from looseball.schema import CORNERS, FPS

TRIGGERS = ("T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7")
LOOSE_TRIGGERS = ("T1", "T2", "T3", "T4", "T5", "T6", "T7")
TRIGGER_LABELS = {
    "T0": "completed pass",
    "T1": "clearance",
    "T2": "failed pass",
    "T3": "shot",
    "T4": "dispossession",
    "T5": "header, non-pass",
    "T6": "unknown end",
    "T7": "completed pass, not controlled",
}
CANDIDATE_RESOLUTIONS = ("recovery", "kept")
MIN_GAP = 3  # frames
CONTACT_ANGLE_DEG = 30.0
CONTACT_SPEED_CHANGE = 3.0  # m/s
CONTACT_PLAYER_RADIUS = 1.5  # metres
CONTACT_EDGE = 2  # frames: contacts are tested from release + 2 to pickup - 2
IMMEDIATE_LEAD = 0.5  # seconds
RADIUS = 15.0  # metres
GATE_SHARE = 0.85


def trigger_class(end_kind, end_result, header, start_kind_next) -> pd.Series:
    """Trigger class of a pair from possession i (and, for T7, how i+1 started); DESIGN.md order."""
    completed = end_kind.eq("pass") & end_result.eq("success")
    conditions = [
        header.astype(bool) & ~end_kind.isin(["pass", "shot"]),
        end_kind.eq("clearance"),
        end_kind.eq("pass") & end_result.eq("fail"),
        end_kind.eq("shot"),
        end_kind.eq("loss"),
        end_kind.eq("unknown"),
        completed & start_kind_next.isin(CANDIDATE_RESOLUTIONS),
        completed,
    ]
    choices = ["T5", "T1", "T2", "T3", "T4", "T6", "T7", "T0"]
    return pd.Series(np.select(conditions, choices, default="other"), index=end_kind.index)


def possession_pairs(possessions: pd.DataFrame) -> pd.DataFrame:
    """Consecutive possession pairs with drop rules, classes, gap and the candidate flag.

    DESIGN.md, Episodes. Columns of possession i carry the suffix _i, of i+1 the suffix _next.
    """
    pp = possessions.sort_values(["start_frame", "event_index"], kind="stable").reset_index(drop=True)
    a = pp.iloc[:-1].reset_index(drop=True).add_suffix("_i")
    b = pp.iloc[1:].reset_index(drop=True).add_suffix("_next")
    p = pd.concat([a, b], axis=1)
    p.insert(0, "match_id", pp["match_id"].iloc[0] if len(pp) else np.nan)
    p.insert(1, "seq_i", np.arange(len(p)))
    p.insert(2, "seq_next", np.arange(1, len(p) + 1))
    dropped = (
        (p["period_id_i"] != p["period_id_next"])
        | p["start_kind_next"].eq("restart")
        | p["end_result_i"].eq("offside")
        | p["interruption_after_i"].astype(bool)
        | p["interruption_before_next"].astype(bool)
        | p["end_kind_i"].eq("foul")
    )
    p["retained"] = ~dropped
    p["gap"] = p["start_frame_next"] - p["end_frame_i"]
    p["release_frame"] = p["end_frame_i"]
    p["pickup_frame"] = p["start_frame_next"]
    p["trigger"] = trigger_class(p["end_kind_i"], p["end_result_i"], p["header_i"], p["start_kind_next"])
    p["resolution"] = p["start_kind_next"]
    p["continuity"] = np.select(
        [p["player_id_i"] == p["player_id_next"], p["team_id_i"] == p["team_id_next"]],
        ["same player", "same team"],
        default="change of team",
    )
    gk_save = p["trigger"].eq("T3") & p["goalkeeper_next"].astype(bool)
    p["candidate"] = (
        p["retained"]
        & p["trigger"].isin(LOOSE_TRIGGERS)
        & p["resolution"].isin(CANDIDATE_RESOLUTIONS)
        & ~gk_save
        & (p["continuity"] != "same player")
        & (p["gap"] >= MIN_GAP)
    )
    return p


def player_columns(tracking: pd.DataFrame) -> list[str]:
    return [
        c[: -len("_detected")] for c in tracking.columns if c.endswith("_detected") and c != "ball_detected"
    ]


def long_players(tracking: pd.DataFrame) -> pd.DataFrame:
    """Players as rows (frame, column_id, x, y, detected), only where the player is present."""
    parts = []
    frames = tracking["frame"].to_numpy()
    for cid in player_columns(tracking):
        x = tracking[f"{cid}_x"].to_numpy(dtype=float)
        here = ~np.isnan(x)
        parts.append(
            pd.DataFrame(
                {
                    "frame": frames[here],
                    "column_id": cid,
                    "x": x[here],
                    "y": tracking[f"{cid}_y"].to_numpy(dtype=float)[here],
                    "detected": tracking[f"{cid}_detected"].fillna(False).to_numpy(dtype=bool)[here],
                }
            )
        )
    if not parts:
        return pd.DataFrame({"frame": [], "column_id": [], "x": [], "y": [], "detected": []})
    return pd.concat(parts, ignore_index=True).sort_values("frame", kind="stable").reset_index(drop=True)


def ball_kinematics(bx: np.ndarray, by: np.ndarray, t: np.ndarray):
    """Horizontal speed into and out of frames t and the turn at t in degrees (0 when not moving)."""
    vin = np.stack([bx[t] - bx[t - 1], by[t] - by[t - 1]], axis=1) * FPS
    vout = np.stack([bx[t + 1] - bx[t], by[t + 1] - by[t]], axis=1) * FPS
    s_in, s_out = np.hypot(*vin.T), np.hypot(*vout.T)
    moving = (s_in > 0) & (s_out > 0)
    cos = np.where(moving, (vin * vout).sum(axis=1) / np.where(moving, s_in * s_out, 1.0), 1.0)
    return s_in, s_out, np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def _in_view(corners: np.ndarray, x: float, y: float) -> bool:
    if np.isnan(corners).any() or np.isnan(x) or np.isnan(y):
        return False
    return bool(MplPath(corners).contains_point((x, y)))


def find_episodes(
    possessions: pd.DataFrame,
    tracking: pd.DataFrame,
    players: pd.DataFrame,
    radius: float = RADIUS,
) -> pd.DataFrame:
    """Loose-ball episodes of one match, with their window structure and flags.

    Implements DESIGN.md, "Episodes" and "Window structure" (step 1, revision 3), with the
    measured leg the last leg (step 2, D1), and the step 2 flags.

    Inputs: possessions, tracking and players tables of one match (looseball.schema).
    Output: one row per candidate episode (DESIGN.md "candidate episode"), with the pair
    (seq_i, seq_next, trigger, resolution, continuity, gap, release_frame, pickup_frame,
    period_id, team_id_i, player_id_i, team_id_next and player_id_next, the winner, which never
    enters the definition), pickup_x and pickup_y (ball on the pickup frame), contacts
    (n_contacts, contact_frames), legs (n_legs, leg1_start, leg1_end, leg2_start, leg2_end),
    anchors (anchor1_frame, and anchor_frame, the last-leg anchor that is measured), lead_s,
    anchored, immediate (lead under 0.5 s), and the camera gate D7 at `radius`
    (n_in_radius, n_detected_in_radius, winner_detected_pickup, kept).
    """
    if not (tracking["frame"].to_numpy() == np.arange(len(tracking))).all():
        raise ValueError("tracking frames must be consecutive from 0")
    p = possession_pairs(possessions)
    p = p[p["candidate"]].reset_index(drop=True)
    column_of = players.set_index("id")["column_id"]
    pl = long_players(tracking)
    pl_frames, pl_x, pl_y = pl["frame"].to_numpy(), pl["x"].to_numpy(), pl["y"].to_numpy()
    pl_det, pl_col = pl["detected"].to_numpy(dtype=bool), pl["column_id"].to_numpy()
    bx, by = tracking["ball_x"].to_numpy(dtype=float), tracking["ball_y"].to_numpy(dtype=float)
    bdet = tracking["ball_detected"].fillna(False).to_numpy(dtype=bool)
    corners = np.stack(
        [tracking[[f"camera_{c}_x", f"camera_{c}_y"]].to_numpy(dtype=float) for c in CORNERS], axis=1
    )

    def at(f: int) -> slice:
        lo, hi = np.searchsorted(pl_frames, [f, f + 1])
        return slice(lo, hi)

    rows = []
    for r in p.itertuples(index=False):
        rel, pk = int(r.release_frame), int(r.pickup_frame)
        px, py = bx[pk], by[pk]
        t = np.arange(rel + CONTACT_EDGE, pk - CONTACT_EDGE + 1)
        evaluable = t[bdet[t - 1] & bdet[t] & bdet[t + 1]]
        s_in, s_out, angle = ball_kinematics(bx, by, evaluable)
        changed = (angle > CONTACT_ANGLE_DEG) | (np.abs(s_out - s_in) > CONTACT_SPEED_CHANGE)
        flagged = []
        for f in evaluable[changed]:
            s = at(int(f))
            if (np.hypot(pl_x[s] - bx[f], pl_y[s] - by[f]) <= CONTACT_PLAYER_RADIUS).any():
                flagged.append(int(f))
        contacts = [f for i, f in enumerate(flagged) if i == 0 or f - flagged[i - 1] > 1]

        view = np.array([_in_view(corners[f], px, py) for f in range(rel, pk + 1)])

        def anchor(start: int, end: int, view=view, rel=rel):
            hits = np.flatnonzero(view[start - rel : end - rel + 1])
            return start + int(hits[0]) if len(hits) else None

        leg1 = (rel, contacts[0] if contacts else pk)
        leg2 = (contacts[-1] if contacts else rel, pk)
        a1, a2 = anchor(*leg1), anchor(*leg2)
        out = {
            "pickup_x": px,
            "pickup_y": py,
            "n_contacts": len(contacts),
            "contact_frames": ";".join(map(str, contacts)),
            "n_legs": len(contacts) + 1,
            "leg1_start": leg1[0],
            "leg1_end": leg1[1],
            "leg2_start": leg2[0],
            "leg2_end": leg2[1],
            "anchor1_frame": a1,
            "anchor_frame": a2,
            "anchored": a2 is not None,
            "lead_s": (pk - a2) / FPS if a2 is not None else np.nan,
        }
        s = at(pk)
        winner = pl_col[s] == column_of.get(r.player_id_next, f"unknown_{r.player_id_next}")
        out["winner_detected_pickup"] = bool((winner & pl_det[s]).any())
        if a2 is None:
            out["n_in_radius"], out["n_detected_in_radius"] = 0, 0
        else:
            s = at(a2)
            near = np.hypot(pl_x[s] - px, pl_y[s] - py) <= radius
            out["n_in_radius"], out["n_detected_in_radius"] = int(near.sum()), int((near & pl_det[s]).sum())
        rows.append(out)

    m = pd.DataFrame(rows, index=p.index) if rows else pd.DataFrame(index=p.index)
    keep = ["match_id", "seq_i", "seq_next", "trigger", "resolution", "continuity", "gap", "release_frame",
            "pickup_frame", "period_id_i", "team_id_i", "player_id_i", "team_id_next", "player_id_next"]  # fmt: skip
    ep = pd.concat([p[keep], m], axis=1).rename(columns={"period_id_i": "period_id"})
    if ep.empty:
        return ep
    ep["anchor_frame"] = ep["anchor_frame"].astype("Int64")
    ep["anchor1_frame"] = ep["anchor1_frame"].astype("Int64")
    ep["immediate"] = ep["anchored"] & (ep["lead_s"] < IMMEDIATE_LEAD)
    n, k = ep["n_in_radius"], ep["n_detected_in_radius"]
    ep["kept"] = ep["anchored"] & ((n == 0) | (k >= GATE_SHARE * n)) & ep["winner_detected_pickup"]
    return ep
