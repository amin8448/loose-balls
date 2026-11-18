"""What would have been enough (step 3, 3h; DESIGN.md "3h. What would have been enough").

Report-only. For each lost ball, from the race at the anchor and the frozen reach model, the
displacement of the best-placed losing player that makes the race level under the model (after
the post hoc revision R1 of 2026-11-18, the enough change is this move only). Nothing is fitted.
Never "would have won" or "what should have happened".

The frozen reach model (DataBallPy "shaw") is t = reaction + |pickup - (p + reaction x v)| / top
speed. It has no turning term, so moving the start point along the line from the drifted position
p + reaction x v to the pickup point by top speed x D lowers the time by exactly D. Under the
pleuler variant (used only for the V3 stability check) the displacement is found by bisection.

The smallest redirection (a rotation of one losing player's velocity at fixed speed) is kept as a
report-only quantity for the audit tables (redirection()); it is in no export.
"""

import numpy as np
import pandas as pd

from looseball.race import REACTION, TOP_SPEED, TURNING_PENALTY, ReachModel

TIE = 1e-9  # seconds for reach times, radians for rotations
BISECTION_STEPS = 80
TYPES = ("move", "already_favourite", "no_player_in_race")
COLUMNS = ["deficit_s", "metres_short", "enough_type", "enough_player", "enough_player_gk",
           "enough_player_extrapolated"]  # fmt: skip
REDIRECT_COLUMNS = ["redirect_player", "redirect_degrees"]


def _pick(table: pd.DataFrame, value: str) -> pd.Series:
    """The row with the smallest `value`; ties within TIE broken by distance, then column_id."""
    lowest = table[value].min()
    tied = table[table[value] <= lowest + TIE]
    return tied.sort_values(["dist", "column_id"], kind="stable").iloc[0]


def rotation_closed_form(d: float, r: float, big_r: float, phi: float) -> float:
    """Smallest rotation (radians) of a velocity of fixed speed that brings the drifted position
    within big_r of the pickup point, without a turning term; NaN when no rotation does.

    d: distance from the player to the pickup point; r: reaction x speed; big_r: top speed x
    (t_w - reaction); phi: angle between the velocity and the direction to the pickup point.
    """
    if d <= 0 or r <= 0 or abs(d - r) > big_r:
        return np.nan
    theta = np.arccos(np.clip((d * d + r * r - big_r * big_r) / (2 * d * r), -1.0, 1.0))
    return max(0.0, phi - theta)


def _rotate(u: np.ndarray, angle: float) -> np.ndarray:
    c, s = np.cos(angle), np.sin(angle)
    return np.array([c * u[0] - s * u[1], s * u[0] + c * u[1]])


def rotation_bisection(model: ReachModel, pos, vel, target, t_w: float) -> float:
    """Smallest rotation (radians) under any reach model whose time increases with the angle
    between the velocity and the direction to the pickup point (used for pleuler); NaN when none."""
    pos, vel, target = (np.asarray(a, float) for a in (pos, vel, target))
    to_target = target - pos
    d, speed = np.hypot(*to_target), np.hypot(*vel)
    if d <= 0 or speed <= 0:
        return np.nan
    u = to_target / d
    phi = np.arccos(np.clip(vel @ u / speed, -1.0, 1.0))
    side = 1.0 if (u[0] * vel[1] - u[1] * vel[0]) >= 0 else -1.0

    def time_at(alpha):  # velocity at angle alpha from the direction to the pickup point
        return model.tti(pos, target, speed * _rotate(u, side * alpha))

    if time_at(0.0) > t_w + TIE:
        return np.nan
    if time_at(phi) <= t_w:
        return 0.0
    lo, hi = 0.0, phi  # time_at(lo) <= t_w < time_at(hi)
    for _ in range(BISECTION_STEPS):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if time_at(mid) <= t_w else (lo, mid)
    return phi - lo


def displacement_bisection(model: ReachModel, pos, vel, target, t_w: float) -> float:
    """Displacement (metres) of the start point along the line from the drifted position to the
    pickup point that brings the reach time to t_w (used for pleuler)."""
    pos, vel, target = (np.asarray(a, float) for a in (pos, vel, target))
    drift = target - (pos + model.reaction_time * vel)
    length = np.hypot(*drift)
    if model.tti(pos, target, vel) <= t_w:
        return 0.0
    w = drift / length
    lo, hi = 0.0, length  # at hi the drifted position is the pickup point: time = reaction <= t_w
    for _ in range(BISECTION_STEPS):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if model.tti(pos + mid * w, target, vel) <= t_w else (mid, hi)
    return hi


def _sides(race: pd.DataFrame, loser_side: str):
    losing = race[race["side"] == loser_side]
    t_w = float(race.loc[race["side"] != loser_side, "t_dynamic"].min())
    deficit = float(losing["t_dynamic"].min()) - t_w
    return losing[~losing["empty_team"].astype(bool)], t_w, deficit


def enough_one(race: pd.DataFrame, loser_side: str, verdict: str, target, reaction: float = REACTION,
               top_speed: float = TOP_SPEED, turning_penalty: str = TURNING_PENALTY) -> dict:  # fmt: skip
    """The 3h quantities of one lost ball.

    race: that episode's rows of reach_times() (both sides, empty-team rows included); loser_side:
    "releasing" or "other"; verdict: the ball's verdict; target: the pickup point (x, y).
    Output: deficit_s, metres_short (blank unless D > 0 and a losing player is in the race),
    enough_type (blank after the anchor, then already_favourite, no_player_in_race, move),
    enough_player (column_id of the best-placed player, move only), enough_player_gk,
    enough_player_extrapolated.
    """
    model = ReachModel(turning_penalty, reaction_time=reaction, max_velocity=top_speed)
    target = np.asarray(target, float)
    players, t_w, deficit = _sides(race, loser_side)
    out = dict.fromkeys(COLUMNS)
    out["deficit_s"] = deficit
    best = _pick(players, "t_dynamic") if not players.empty else None
    if deficit > 0 and best is not None:
        if model.turning_penalty == "shaw":
            out["metres_short"] = top_speed * deficit
        else:
            vel = np.nan_to_num(np.array([best.vx, best.vy], float))
            out["metres_short"] = displacement_bisection(model, (best.x, best.y), vel, target, t_w)
    if verdict == "after the anchor":
        return out
    if deficit <= 0:
        out["enough_type"] = "already_favourite"
        return out
    if best is None:
        out["enough_type"] = "no_player_in_race"
        return out
    out.update(
        enough_type="move",
        enough_player=best["column_id"],
        enough_player_gk=bool(best["goalkeeper"]),
        enough_player_extrapolated=not bool(best["detected"]),
    )
    return out


def redirection_one(race: pd.DataFrame, loser_side: str, target, reaction: float = REACTION,
                    top_speed: float = TOP_SPEED, turning_penalty: str = TURNING_PENALTY) -> dict:  # fmt: skip
    """Report-only (since R1): the smallest rotation of one losing player's velocity, at fixed
    speed, that makes the race level; NaN and None when D <= 0, nobody is in the race, or no
    rotation does. Output: redirect_player (column_id), redirect_degrees."""
    model = ReachModel(turning_penalty, reaction_time=reaction, max_velocity=top_speed)
    target = np.asarray(target, float)
    players, t_w, deficit = _sides(race, loser_side)
    out = {"redirect_player": None, "redirect_degrees": np.nan}
    if deficit <= 0 or players.empty:
        return out
    rotations = []
    for p in players.itertuples(index=False):
        vel = np.array([p.vx, p.vy], float)
        speed = float(np.hypot(*vel)) if np.isfinite(vel).all() else 0.0
        if p.velocity_missing or speed <= 0:
            continue
        to_target = target - np.array([p.x, p.y], float)
        d = float(np.hypot(*to_target))
        if d <= 0:
            continue
        if model.turning_penalty == "shaw":
            phi = float(np.arccos(np.clip(vel @ to_target / (speed * d), -1.0, 1.0)))
            rot = rotation_closed_form(d, reaction * speed, top_speed * (t_w - reaction), phi)
        else:
            rot = rotation_bisection(model, (p.x, p.y), vel, target, t_w)
        if np.isfinite(rot):
            rotations.append({"column_id": p.column_id, "dist": p.dist, "rotation": rot})
    if rotations:
        chosen = _pick(pd.DataFrame(rotations), "rotation")
        out = {
            "redirect_player": chosen["column_id"],
            "redirect_degrees": float(np.degrees(chosen["rotation"])),
        }
    return out


def enough(reach: pd.DataFrame, balls: pd.DataFrame, reaction: float = REACTION, top_speed: float = TOP_SPEED,
           turning_penalty: str = TURNING_PENALTY) -> pd.DataFrame:  # fmt: skip
    """The 3h quantities for every lost ball (DESIGN.md "3h. What would have been enough").

    reach: reach_times() output covering the balls; balls: one row per lost ball with match_id,
    seq_i, loser_side and verdict (from decompose()) and pickup_x, pickup_y (from find_episodes()).
    Immediate episodes are not lost balls of the analysis set and are not expected here.
    Output: match_id, seq_i and COLUMNS, in the order of `balls`.
    """
    groups = dict(tuple(reach.groupby(["match_id", "seq_i"], sort=False)))
    rows = []
    for b in balls.itertuples(index=False):
        race = groups[(b.match_id, b.seq_i)]
        values = enough_one(race, b.loser_side, b.verdict, (b.pickup_x, b.pickup_y), reaction, top_speed,
                            turning_penalty)  # fmt: skip
        rows.append({"match_id": b.match_id, "seq_i": b.seq_i, **values})
    out = pd.DataFrame(rows, columns=["match_id", "seq_i", *COLUMNS])
    for c in ("enough_player_gk", "enough_player_extrapolated"):
        out[c] = out[c].astype("boolean")
    for c in ("deficit_s", "metres_short"):
        out[c] = out[c].astype(float)
    return out


def redirection(reach: pd.DataFrame, balls: pd.DataFrame, reaction: float = REACTION, top_speed: float = TOP_SPEED,
                turning_penalty: str = TURNING_PENALTY) -> pd.DataFrame:  # fmt: skip
    """Report-only (since R1): redirection_one() for every ball of `balls` (match_id, seq_i,
    loser_side, pickup_x, pickup_y). Output: match_id, seq_i, redirect_player, redirect_degrees."""
    groups = dict(tuple(reach.groupby(["match_id", "seq_i"], sort=False)))
    rows = [
        {"match_id": b.match_id, "seq_i": b.seq_i,
         **redirection_one(groups[(b.match_id, b.seq_i)], b.loser_side, (b.pickup_x, b.pickup_y), reaction,
                           top_speed, turning_penalty)}
        for b in balls.itertuples(index=False)
    ]  # fmt: skip
    out = pd.DataFrame(rows, columns=["match_id", "seq_i", *REDIRECT_COLUMNS])
    out["redirect_degrees"] = out["redirect_degrees"].astype(float)
    return out
