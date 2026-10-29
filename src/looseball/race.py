"""The race at the anchor (step 2, D2 and D3).

Players in the race: every player of both teams within the radius of the pickup point on the
anchor frame (the last-leg anchor, DESIGN.md), goalkeepers included and flagged (roster field
player_role.acronym == "GK"). Reach time: DataBallPy's time to intercept from the player's
position and smoothed velocity on the anchor frame to the pickup point; static reach time: the
same with velocity zero. Team best time: the minimum over the team's players in the race. A team
with nobody in the race gets reaction_time + radius / max_velocity, the time of a standing player
on the radius, and is flagged. Sides are named from the releasing team (team of possession i).
The winner is not read here.
"""

import numpy as np
import pandas as pd
from databallpy.optimization.constraints import TTIConstraint

from looseball import io, paths, velocities

REACTION_TIME = 0.7  # DataBallPy default
MAX_VELOCITY = 5.0  # DataBallPy default, m/s
RADIUS = 15.0
TURNING_PENALTY = "shaw"
SIDES = ("releasing", "other")
CA_ACCELERATION = 3.0  # m/s^2, constant-acceleration model (report-only)


class ReachModel(TTIConstraint):
    """DataBallPy's TTIConstraint without a Game: only the parameters that tti() reads are set.

    tti() is the package's method, unchanged.
    """

    def __init__(
        self,
        turning_penalty: str = TURNING_PENALTY,
        reaction_time: float = REACTION_TIME,
        max_velocity: float = MAX_VELOCITY,
    ):
        if not isinstance(turning_penalty, str) or turning_penalty.lower() not in ("shaw", "pleuler"):
            raise ValueError(f'turning_penalty must be "shaw" or "pleuler", not {turning_penalty!r}')
        self.reaction_time = reaction_time
        self.max_velocity = max_velocity
        self.turning_penalty = turning_penalty.lower()
        self.max_time_to_intercept_seconds = np.inf

    def reach_times(self, positions: np.ndarray, velocities: np.ndarray, target) -> np.ndarray:
        """Time for each player (rows of positions and velocities) to reach target, one call each."""
        target = np.asarray(target, dtype=float)
        return np.array(
            [
                self.tti(np.asarray(p, float), target, np.asarray(v, float))
                for p, v in zip(positions, velocities)
            ]
        )

    def empty_team_time(self, radius: float) -> float:
        return self.reaction_time + radius / self.max_velocity


class ConstantAccelerationModel:
    """Report-only reach model (MT1 addition 2), a candidate follow-up to the package.

    The player accelerates toward the pickup point from his current velocity at `acceleration`,
    capped at `max_velocity`, in one dimension along the line to the pickup point: the initial
    speed is the velocity projected on that line (negative when moving away; above the cap it
    starts at the cap), the sideways component is ignored, and there is no reaction time.
    """

    def __init__(self, acceleration: float = CA_ACCELERATION, max_velocity: float = MAX_VELOCITY):
        self.acceleration = acceleration
        self.max_velocity = max_velocity

    def reach_times(self, positions: np.ndarray, velocities: np.ndarray, target) -> np.ndarray:
        to_target = np.asarray(target, dtype=float) - np.asarray(positions, dtype=float)
        d = np.hypot(to_target[:, 0], to_target[:, 1])
        unit = np.divide(to_target, d[:, None], out=np.zeros_like(to_target), where=d[:, None] > 0)
        a, vmax = self.acceleration, self.max_velocity
        v0 = np.minimum((np.asarray(velocities, dtype=float) * unit).sum(axis=1), vmax)
        t_cap = (vmax - v0) / a  # time to reach the cap
        s_cap = v0 * t_cap + 0.5 * a * t_cap**2  # distance covered by then
        t_accelerating = (-v0 + np.sqrt(v0**2 + 2 * a * d)) / a
        t = np.where(d <= s_cap, t_accelerating, t_cap + (d - s_cap) / vmax)
        return np.where(d > 0, t, 0.0)

    def empty_team_time(self, radius: float) -> float:
        return float(self.reach_times(np.array([[radius, 0.0]]), np.zeros((1, 2)), (0.0, 0.0))[0])


def reach_model(
    name: str = "databallpy", turning_penalty: str = TURNING_PENALTY, reaction_time: float = REACTION_TIME
):
    """The reach model by name: "databallpy" (the entry's model) or "constant_acceleration"."""
    if name == "databallpy":
        return ReachModel(turning_penalty, reaction_time=reaction_time)
    if name == "constant_acceleration":
        return ConstantAccelerationModel()
    raise ValueError(f'reach model must be "databallpy" or "constant_acceleration", not {name!r}')


def race_players(
    at_anchor: pd.DataFrame,
    target: tuple[float, float],
    releasing_team: int,
    team_of: pd.Series,
    gk_ids: set,
    radius: float,
    model,
    drop_extrapolated: bool = False,
) -> pd.DataFrame:
    """Players in the race with reach times.

    at_anchor: players on the anchor frame with player_id, x, y, vx, vy and is_detected.
    A player without a velocity (track shorter than the smoothing window) gets velocity zero and
    is flagged velocity_missing.
    """
    p = at_anchor.copy()
    p["dist"] = np.hypot(p["x"] - target[0], p["y"] - target[1])
    p = p[p["dist"] <= radius]
    p["is_detected"] = p["is_detected"].fillna(False).astype(bool)
    if drop_extrapolated:
        p = p[p["is_detected"]]
    p["team_id"] = team_of.reindex(p["player_id"]).to_numpy()
    p["side"] = np.where(p["team_id"] == releasing_team, "releasing", "other")
    p["is_gk"] = p["player_id"].isin(gk_ids)
    p["velocity_missing"] = p["vx"].isna() | p["vy"].isna()
    pos = p[["x", "y"]].to_numpy(dtype=float)
    vel = p[["vx", "vy"]].fillna(0.0).to_numpy(dtype=float)
    p["t_static"] = model.reach_times(pos, np.zeros_like(pos), target)
    p["t_dynamic"] = model.reach_times(pos, vel, target)
    return p.reset_index(drop=True)


def team_summary(race: pd.DataFrame, radius: float, model) -> dict:
    """Team best times, counts, nearest distance and flags, by side."""
    empty_time = model.empty_team_time(radius)
    out = {}
    for side in SIDES:
        s = race[race["side"] == side]
        out[f"n_{side}"] = len(s)
        out[f"n_detected_{side}"] = int(s["is_detected"].sum())
        out[f"empty_{side}"] = s.empty
        out[f"best_static_{side}"] = s["t_static"].min() if len(s) else empty_time
        out[f"best_dynamic_{side}"] = s["t_dynamic"].min() if len(s) else empty_time
        out[f"nearest_{side}"] = s["dist"].min() if len(s) else radius
    out["n_gk"] = int(race["is_gk"].sum())
    out["n_extrapolated"] = int((~race["is_detected"]).sum())
    out["n_velocity_missing"] = int(race["velocity_missing"].sum())
    return out


def episode_races(
    match_id: int,
    episodes: pd.DataFrame,
    *,
    radius: float = RADIUS,
    growing_speed: float | None = None,
    turning_penalty: str = TURNING_PENALTY,
    window: int = velocities.WINDOW,
    anchor_shift: int = 0,
    drop_extrapolated: bool = False,
    reaction_time: float = REACTION_TIME,
    model_name: str = "databallpy",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Races for the main pairs of one match that have a last-leg anchor.

    episodes: main pairs with seq_i, anchor2_frame, pickup_frame, pickup_x, pickup_y, team_id_i.
    radius: fixed radius in metres; with growing_speed set (m/s), max(radius, growing_speed * lead).
    anchor_shift: frames added to the last-leg anchor (the "anchor 0.2 s later" variant is 2).
    reaction_time: DataBallPy model only (the 0.35 s variant). model_name: "databallpy" or
    "constant_acceleration" (report-only).
    Returns one row per episode (team summary) and one row per player in the race.
    """
    vel = velocities.match_velocities(match_id, window)
    frames = vel["frame"].to_numpy()
    roster = io.load_roster(match_id)
    team_of = roster.set_index("id")["team_id"]
    gk_ids = set(roster.loc[roster["player_role.acronym"] == "GK", "id"])
    model = reach_model(model_name, turning_penalty, reaction_time)

    rows, players = [], []
    for e in episodes[episodes["anchor2_frame"].notna()].itertuples(index=False):
        anchor = int(e.anchor2_frame) + anchor_shift
        lead = (int(e.pickup_frame) - anchor) / paths.FPS
        r = max(radius, growing_speed * lead) if growing_speed else radius
        lo, hi = np.searchsorted(frames, [anchor, anchor + 1])
        target = (float(e.pickup_x), float(e.pickup_y))
        race = race_players(
            vel.iloc[lo:hi], target, e.team_id_i, team_of, gk_ids, r, model, drop_extrapolated
        )
        key = {"match_id": match_id, "seq_i": e.seq_i}
        rows.append(
            {**key, "anchor_frame": anchor, "lead_s": lead, "radius_m": r, **team_summary(race, r, model)}
        )
        players.append(race.assign(**key))
    cols = ["match_id", "seq_i", "player_id", "team_id", "side", "is_gk", "is_detected", "velocity_missing"]
    cols += ["x", "y", "vx", "vy", "dist", "t_static", "t_dynamic"]
    player_table = pd.concat(players, ignore_index=True)[cols] if players else pd.DataFrame(columns=cols)
    return pd.DataFrame(rows), player_table
