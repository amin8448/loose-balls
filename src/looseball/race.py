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


def race_players(
    at_anchor: pd.DataFrame,
    target: tuple[float, float],
    releasing_team: int,
    team_of: pd.Series,
    gk_ids: set,
    radius: float,
    model: ReachModel,
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


def team_summary(race: pd.DataFrame, radius: float, model: ReachModel) -> dict:
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
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Races for the main pairs of one match that have a last-leg anchor.

    episodes: main pairs with seq_i, anchor2_frame, pickup_frame, pickup_x, pickup_y, team_id_i.
    radius: fixed radius in metres; with growing_speed set (m/s), max(radius, growing_speed * lead).
    anchor_shift: frames added to the last-leg anchor (the "anchor 0.2 s later" variant is 2).
    Returns one row per episode (team summary) and one row per player in the race.
    """
    vel = velocities.match_velocities(match_id, window)
    frames = vel["frame"].to_numpy()
    roster = io.load_roster(match_id)
    team_of = roster.set_index("id")["team_id"]
    gk_ids = set(roster.loc[roster["player_role.acronym"] == "GK", "id"])
    model = ReachModel(turning_penalty)

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
