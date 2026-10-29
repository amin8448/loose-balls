"""Reach times at the anchor (step 2, D2 and D3): reach_times.

Players in the race: every player of both teams within the radius of the pickup point on the
anchor frame, goalkeepers included and flagged. Reach time: DataBallPy's time to intercept
(TTIConstraint.tti, DataBallPy develop 3f9de8d) from the player's position and smoothed
velocity on the anchor frame to the pickup point; static: the same with velocity zero.
"""

import numpy as np
import pandas as pd
from databallpy.optimization.constraints import TTIConstraint

from looseball.schema import FPS
from looseball.velocities import WINDOW, tracking_velocities

RADIUS = 15.0
TURNING_PENALTY = "shaw"
REACTION = 0.7  # DataBallPy default, seconds
TOP_SPEED = 5.0  # DataBallPy default, m/s
CA_ACCELERATION = 3.0  # m/s^2, the report-only constant-acceleration model
SIDES = ("releasing", "other")


class ReachModel(TTIConstraint):
    """DataBallPy's TTIConstraint without a Game: only the parameters tti() reads are set.

    tti() is the package's method, unchanged.
    """

    def __init__(self, turning_penalty: str = TURNING_PENALTY, reaction_time: float = REACTION,
                 max_velocity: float = TOP_SPEED):  # fmt: skip
        if not isinstance(turning_penalty, str) or turning_penalty.lower() not in ("shaw", "pleuler"):
            raise ValueError(f'turning_penalty must be "shaw" or "pleuler", not {turning_penalty!r}')
        self.reaction_time = reaction_time
        self.max_velocity = max_velocity
        self.turning_penalty = turning_penalty.lower()
        self.max_time_to_intercept_seconds = np.inf

    def reach_times(self, positions: np.ndarray, velocities: np.ndarray, target) -> np.ndarray:
        target = np.asarray(target, dtype=float)
        return np.array(
            [
                self.tti(np.asarray(p, float), target, np.asarray(v, float))
                for p, v in zip(positions, velocities)
            ]
        )

    def empty_team_time(self, radius: float) -> float:
        """A team with nobody in the race: a standing player on the radius."""
        return self.reaction_time + radius / self.max_velocity


class ConstantAccelerationModel:
    """Report-only reach model: acceleration toward the pickup point from the current velocity,
    capped at the top speed, along the line to the pickup point (velocity projected on it,
    sideways component ignored, no reaction time), solved in closed form."""

    def __init__(self, acceleration: float = CA_ACCELERATION, max_velocity: float = TOP_SPEED):
        self.acceleration = acceleration
        self.max_velocity = max_velocity

    def reach_times(self, positions: np.ndarray, velocities: np.ndarray, target) -> np.ndarray:
        to_target = np.asarray(target, dtype=float) - np.asarray(positions, dtype=float)
        d = np.hypot(to_target[:, 0], to_target[:, 1])
        unit = np.divide(to_target, d[:, None], out=np.zeros_like(to_target), where=d[:, None] > 0)
        a, vmax = self.acceleration, self.max_velocity
        v0 = np.minimum((np.asarray(velocities, dtype=float) * unit).sum(axis=1), vmax)
        t_cap = (vmax - v0) / a
        s_cap = v0 * t_cap + 0.5 * a * t_cap**2
        t_accelerating = (-v0 + np.sqrt(v0**2 + 2 * a * d)) / a
        t = np.where(d <= s_cap, t_accelerating, t_cap + (d - s_cap) / vmax)
        return np.where(d > 0, t, 0.0)

    def empty_team_time(self, radius: float) -> float:
        return float(self.reach_times(np.array([[radius, 0.0]]), np.zeros((1, 2)), (0.0, 0.0))[0])


def reach_model(name: str = "databallpy", turning_penalty: str = TURNING_PENALTY, reaction: float = REACTION,
                top_speed: float = TOP_SPEED):  # fmt: skip
    """ "databallpy" (the entry's model) or "constant_acceleration" (report-only)."""
    if name == "databallpy":
        return ReachModel(turning_penalty, reaction_time=reaction, max_velocity=top_speed)
    if name == "constant_acceleration":
        return ConstantAccelerationModel(max_velocity=top_speed)
    raise ValueError(f'reach model must be "databallpy" or "constant_acceleration", not {name!r}')


def reach_times(
    episodes: pd.DataFrame,
    tracking: pd.DataFrame,
    players: pd.DataFrame,
    radius: float = RADIUS,
    turning_penalty: str = TURNING_PENALTY,
    reaction: float = REACTION,
    top_speed: float = TOP_SPEED,
    smoothing_window: int = WINDOW,
    *,
    growing_speed: float | None = None,
    anchor_shift: int = 0,
    drop_extrapolated: bool = False,
    model: str = "databallpy",
) -> pd.DataFrame:
    """Per-player static and dynamic reach times at the anchor (step 2, D2 to D4; DESIGN.md
    "Step 2 measures").

    Inputs: episodes from find_episodes for one match (only anchored episodes are used), and
    that match's tracking and players tables. radius in metres; with growing_speed set (m/s)
    the radius is max(radius, growing_speed x lead). anchor_shift adds frames to the anchor;
    drop_extrapolated leaves out players not detected on the anchor frame; model is
    "databallpy" or "constant_acceleration" (report-only; turning_penalty and reaction then
    do not apply).

    Output: one row per player in the race with match_id, seq_i, anchor_frame, lead_s,
    radius_m, column_id, team_id, side ("releasing": the team of possession i, or "other"),
    goalkeeper, detected, velocity_missing (track shorter than the window: velocity zero),
    x, y, vx, vy, dist, t_static, t_dynamic, empty_team (False); and for a team with nobody in
    the race one row with empty_team True, dist equal to the radius and both times set to the
    empty-team time (a standing player on the radius).
    """
    m = reach_model(model, turning_penalty, reaction, top_speed)
    vel = tracking_velocities(tracking, smoothing_window)
    frames = vel["frame"].to_numpy()
    team_of = players.set_index("column_id")["team_id"]
    gk = set(players.loc[players["position"] == "goalkeeper", "column_id"])
    teams = sorted(players["team_id"].dropna().unique())
    rows = []
    for e in episodes[episodes["anchored"].astype(bool)].itertuples(index=False):
        anchor = int(e.anchor_frame) + anchor_shift
        lead = (int(e.pickup_frame) - anchor) / FPS
        r = max(radius, growing_speed * lead) if growing_speed else radius
        lo, hi = np.searchsorted(frames, [anchor, anchor + 1])
        target = (float(e.pickup_x), float(e.pickup_y))
        p = vel.iloc[lo:hi].copy()
        p["dist"] = np.hypot(p["x"] - target[0], p["y"] - target[1])
        p = p[p["dist"] <= r]
        p["detected"] = p["detected"].fillna(False).astype(bool)
        if drop_extrapolated:
            p = p[p["detected"]]
        p["team_id"] = team_of.reindex(p["column_id"]).to_numpy()
        p["side"] = np.where(p["team_id"] == e.team_id_i, "releasing", "other")
        p["goalkeeper"] = p["column_id"].isin(gk)
        p["velocity_missing"] = p["vx"].isna() | p["vy"].isna()
        pos = p[["x", "y"]].to_numpy(dtype=float)
        p["t_static"] = m.reach_times(pos, np.zeros_like(pos), target)
        p["t_dynamic"] = m.reach_times(pos, p[["vx", "vy"]].fillna(0.0).to_numpy(dtype=float), target)
        p["empty_team"] = False
        key = {
            "match_id": e.match_id,
            "seq_i": e.seq_i,
            "anchor_frame": anchor,
            "lead_s": lead,
            "radius_m": r,
        }
        rows.append(p.assign(**key))
        for side in SIDES:
            if not (p["side"] == side).any():
                team = (
                    e.team_id_i
                    if side == "releasing"
                    else next((t for t in teams if t != e.team_id_i), np.nan)
                )
                empty = m.empty_team_time(r)
                rows.append(pd.DataFrame([{**key, "team_id": team, "side": side, "dist": r, "t_static": empty,
                                           "t_dynamic": empty, "empty_team": True}]))  # fmt: skip
    cols = ["match_id", "seq_i", "anchor_frame", "lead_s", "radius_m", "column_id", "team_id", "side", "goalkeeper",
            "detected", "velocity_missing", "x", "y", "vx", "vy", "dist", "t_static", "t_dynamic", "empty_team"]  # fmt: skip
    if not rows:
        return pd.DataFrame(columns=cols)
    out = pd.concat([r.reindex(columns=cols) for r in rows], ignore_index=True)
    out["empty_team"] = out["empty_team"].astype(bool)
    return out
