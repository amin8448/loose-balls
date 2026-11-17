"""Path check (step 3, 3h; report-only; AUDIT.md "Path check: procedure").

Reach times are measured to the pickup point, where the winner took the ball, so the loser may
look worse placed by construction. This check asks which team could first reach the ball
anywhere along its tracked path from the anchor to the pickup, from anchor-frame positions of all
rostered players of each team under the frozen reach model. It changes no verdict.
"""

import numpy as np
import pandas as pd

from looseball.race import ReachModel
from looseball.schema import FPS

AERIAL_Z = 1.8  # metres; DESIGN.md "aerial episode"
TOLERANCES = (0.3, 0.0)  # seconds; 0.3 is the S2 tolerance


def is_ground(tracking: pd.DataFrame, release: int, pickup: int) -> bool:
    """DESIGN.md: aerial when ball z > 1.8 m on any window frame (after the release, up to and
    including the pickup) with the ball detected; ground otherwise."""
    w = tracking.iloc[release + 1 : pickup + 1]
    detected = w["ball_detected"].fillna(False).to_numpy(dtype=bool)
    return not bool((detected & (w["ball_z"].to_numpy(dtype=float) > AERIAL_Z)).any())


def first_reachable(model: ReachModel, pos: np.ndarray, vel: np.ndarray, targets: np.ndarray,
                    budget: np.ndarray) -> int | None:  # fmt: skip
    """Index of the first target whose best reach time over the players is within its budget."""
    if len(pos) == 0 or len(targets) == 0:
        return None
    best = np.min([model.tti(p, targets, v) for p, v in zip(pos, vel)], axis=0)
    hits = np.flatnonzero(best <= budget)
    return int(hits[0]) if len(hits) else None


def favourite(first_a, first_b, a, b) -> str:
    """The team with the earlier first reachable frame; 'tie' on equal frames; 'unreached'."""
    if first_a is None and first_b is None:
        return "unreached"
    if first_b is None or (first_a is not None and first_a < first_b):
        return a
    if first_a is None or first_b < first_a:
        return b
    return "tie"


def path_check(balls: pd.DataFrame, tracking: pd.DataFrame, velocities: pd.DataFrame, players: pd.DataFrame,
               tolerances=TOLERANCES) -> pd.DataFrame:  # fmt: skip
    """Per lost ball of one match: ground flag, and for the static and dynamic versions and each
    tolerance the first reachable frame of the losing and winning team and the path favourite
    ("loser", "winner", "tie" or "unreached"; NaN for aerial balls).

    balls: match_id, seq_i, release_frame, anchor_frame, pickup_frame, losing_team, winning_team.
    velocities: tracking_velocities() of the match (frozen window 5); players: the players table.
    """
    model = ReachModel()
    team_of = players.set_index("column_id")["team_id"]
    rows = []
    for b in balls.itertuples(index=False):
        anchor, pickup = int(b.anchor_frame), int(b.pickup_frame)
        row = {
            "match_id": b.match_id,
            "seq_i": b.seq_i,
            "ground": is_ground(tracking, int(b.release_frame), pickup),
        }
        frames = np.arange(anchor, pickup + 1)
        seg = tracking.iloc[anchor : pickup + 1]
        ok = (
            seg["ball_detected"].fillna(False).to_numpy(dtype=bool)
            & seg[["ball_x", "ball_y"]].notna().all(axis=1).to_numpy()
        )
        frames, targets = frames[ok], seg.loc[ok, ["ball_x", "ball_y"]].to_numpy(dtype=float)
        row["path_frames"] = len(frames)
        at = velocities[(velocities["frame"] == anchor) & velocities["column_id"].isin(team_of.index)]
        at = at[at[["x", "y"]].notna().all(axis=1)]
        teams = team_of.reindex(at["column_id"]).to_numpy()
        for version in ("static", "dynamic"):
            for tol in tolerances:
                key = f"{version} {tol:g}"
                if not row["ground"]:
                    row.update(
                        {
                            f"{key} first loser": np.nan,
                            f"{key} first winner": np.nan,
                            f"{key} favourite": np.nan,
                        }
                    )
                    continue
                budget = (frames - anchor) / FPS + tol
                first = {}
                for side, team in (("loser", b.losing_team), ("winner", b.winning_team)):
                    t = at[teams == team]
                    pos = t[["x", "y"]].to_numpy(dtype=float)
                    vel = (
                        np.zeros_like(pos)
                        if version == "static"
                        else t[["vx", "vy"]].fillna(0.0).to_numpy(dtype=float)
                    )
                    k = first_reachable(model, pos, vel, targets, budget)
                    first[side] = None if k is None else int(frames[k])
                row[f"{key} first loser"] = first["loser"]
                row[f"{key} first winner"] = first["winner"]
                row[f"{key} favourite"] = favourite(first["loser"], first["winner"], "loser", "winner")
        rows.append(row)
    return pd.DataFrame(rows)
