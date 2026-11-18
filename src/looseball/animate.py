"""looseball animate (step 3, 3h): one lost ball as recorded, then, for a move ball, the one
change under the model. Not part of looseball reproduce and not byte-checked.

Part one, "as recorded", from the release frame to the pickup frame, each data frame held for
`hold` seconds; no position is interpolated. Before the anchor: both teams as dots with velocity
arrows (one second of current movement), hollow when not detected, the camera view outlined, the
ball with its trail (hollow at its last detected position when not detected), and the label "drop
zone not yet in view"; no shading and no pickup marker. At the anchor (held 1.5 s) the shading
appears, drawn as in Figure 1 (each team's best dynamic reach time to every point from all of
its players on the frame, under the frozen reach model, as the winning team's margin clipped at
2 s), with the pickup marker, the 15 m race circle and one caption line. From the anchor to the
pickup: recorded positions, shading recomputed on each frame. The pickup frame is held 1 s with
the team that won the ball named.

Part two, labelled "model: one change" throughout, only for enough_type move: the anchor frame
frozen, the best-placed player as a ghost at his recorded spot and at the moved spot (metres_short
along the line from his drifted position to the pickup point), an arrow with the distance, the
shading recomputed with the change, and the label that the model now has the race level; held
3 s. No recorded track is replayed next to a model-driven player.

Players are labelled by shirt number only. Output: mp4 through ffmpeg when available, GIF
otherwise.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import animation
from matplotlib.cm import ScalarMappable
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap
from matplotlib.patches import Circle, Polygon

from looseball import decompose, expectations, find_episodes, reach_times
from looseball.adapters.skillcorner import load_match
from looseball.enough import enough
from looseball.figures import BLUE, GRID, INK, MUTED, NEUTRAL, ORANGE, SURFACE, _pitch
from looseball.race import RADIUS, REACTION, ReachModel
from looseball.schema import CORNERS
from looseball.velocities import tracking_velocities

HOLD = 0.25  # seconds per data frame
ANCHOR_HOLD, PICKUP_HOLD, MODEL_HOLD = 1.5, 1.0, 3.0
MARGIN_CLIP = 2.0
LEVELS = np.arange(-2.0, 2.01, 0.25)
GRID_POINTS = 140
PAD, AROUND_PICKUP = 4.0, 16.0  # metres
FIGSIZE, DPI = (10.0, 8.4), 100  # 1000 x 840 pixels, even for the mp4 encoder


def schedule(release: int, anchor: int, pickup: int, model_part: bool, hold: float = HOLD) -> list:
    """The animation as (stage, data frame, repeats): stage is before, anchor, after, pickup or model."""

    def n(seconds: float) -> int:
        return max(1, round(seconds / hold))

    steps = [("before", f, 1) for f in range(release, anchor)]
    steps.append(("anchor", anchor, n(ANCHOR_HOLD)))
    steps += [("after", f, 1) for f in range(anchor + 1, pickup)]
    if pickup > anchor:
        steps.append(("pickup", pickup, n(PICKUP_HOLD)))
    if model_part:
        steps.append(("model", anchor, n(MODEL_HOLD)))
    return steps


def episode(data, match_id: int, seq_i: int) -> dict:
    """Everything the animation needs for one lost ball of the analysis set, from the public API
    with the frozen parameters."""
    m = load_match(data, match_id)
    ep = find_episodes(m.possessions, m.tracking, m.players)
    a = ep[ep["anchored"].astype(bool) & ep["kept"].astype(bool) & ~ep["immediate"].astype(bool)]
    a = a[a["seq_i"] == seq_i]
    if a.empty:
        raise ValueError(f"episode {seq_i} of match {match_id} is not a lost ball of the analysis set")
    reach = reach_times(a, m.tracking, m.players)
    d = decompose(
        expectations(reach), a[["match_id", "seq_i"]].assign(winning_team=a["team_id_next"].to_numpy())
    )
    balls = d[["match_id", "seq_i", "loser_side", "verdict"]].merge(
        a[["match_id", "seq_i", "pickup_x", "pickup_y"]], on=["match_id", "seq_i"]
    )
    e = enough(reach, balls).iloc[0]
    return {"match": m, "episode": a.iloc[0], "decomposed": d.iloc[0], "enough": e, "race": reach,
            "velocities": tracking_velocities(m.tracking)}  # fmt: skip


def _extent(tracking: pd.DataFrame, ep, pitch) -> tuple:
    path = tracking.loc[int(ep.release_frame) : int(ep.pickup_frame), ["ball_x", "ball_y"]].to_numpy(
        dtype=float
    )
    path = path[np.isfinite(path).all(axis=1)]
    px, py = float(ep.pickup_x), float(ep.pickup_y)
    xs = np.r_[path[:, 0], px - AROUND_PICKUP, px + AROUND_PICKUP]
    ys = np.r_[path[:, 1], py - AROUND_PICKUP, py + AROUND_PICKUP]
    length, width = pitch
    xlim = (max(xs.min() - PAD, -length / 2 - 2), min(xs.max() + PAD, length / 2 + 2))
    ylim = (max(ys.min() - PAD, -width / 2 - 2), min(ys.max() + PAD, width / 2 + 2))
    return xlim, ylim


def margin_grid(players: pd.DataFrame, loser: int, winner: int, gx, gy) -> np.ndarray:
    """The winning team's margin (loser's best dynamic reach time minus winner's), clipped at 2 s,
    from all players of `players` (x, y, vx, vy, team_id), frozen reach model."""
    model = ReachModel()
    grid = np.column_stack([gx.ravel(), gy.ravel()])

    def best(team):
        rows = players[players["team_id"] == team]
        times = [
            model.tti(np.array([p.x, p.y]), grid, np.nan_to_num(np.array([p.vx, p.vy])))
            for p in rows.itertuples()
        ]
        return np.min(times, axis=0) if times else np.full(len(grid), np.inf)

    return np.clip(best(loser) - best(winner), -MARGIN_CLIP, MARGIN_CLIP).reshape(gx.shape)


def moved_spot(enough_row, race: pd.DataFrame, target) -> tuple:
    """The best-placed player's recorded and moved positions (move balls)."""
    p = race[race["column_id"] == enough_row["enough_player"]].iloc[0]
    pos, vel = np.array([p.x, p.y], float), np.nan_to_num(np.array([p.vx, p.vy], float))
    drift = np.asarray(target, float) - (pos + REACTION * vel)
    return pos, pos + float(enough_row["metres_short"]) * drift / np.hypot(*drift)


def animate(data, match_id: int, seq_i: int, out, hold: float = HOLD) -> dict:
    """Write the animation of one lost ball to `out` (.mp4 through ffmpeg when available, else .gif)."""
    s = episode(data, match_id, seq_i)
    m, ep, d, e, race, vel = (
        s["match"],
        s["episode"],
        s["decomposed"],
        s["enough"],
        s["race"],
        s["velocities"],
    )
    loser, winner = int(d["losing_team"]), int(d["winning_team"])
    release, anchor, pickup = int(ep.release_frame), int(ep.anchor_frame), int(ep.pickup_frame)
    target = np.array([ep.pickup_x, ep.pickup_y], float)
    model_part = e["enough_type"] == "move"
    steps = schedule(release, anchor, pickup, model_part, hold)
    names = m.team_names
    team_of = m.players.set_index("column_id")["team_id"]
    vel = vel[vel["frame"].between(release, pickup) & vel["column_id"].isin(team_of.index)].copy()
    vel["team_id"] = team_of.reindex(vel["column_id"]).to_numpy()
    tr = m.tracking
    xlim, ylim = _extent(tr, ep, m.pitch_dimensions)
    gx, gy = np.meshgrid(np.linspace(*xlim, GRID_POINTS), np.linspace(*ylim, GRID_POINTS))
    cmap = LinearSegmentedColormap.from_list("margin", [ORANGE, NEUTRAL, BLUE])
    caption = (
        f"{names[loser]}: {100 * d['p_static_loser']:.1f}% from position, {100 * d['p_dynamic_loser']:.1f}% with "
        f"movement: lost on {d['verdict']}"
    )
    if model_part:
        ghost, moved = moved_spot(e, race, target)
        level = vel[vel["frame"] == anchor].copy()
        level.loc[level["column_id"] == e["enough_player"], ["x", "y"]] = moved
        level_margin = float(
            margin_grid(level, loser, winner, np.array([[target[0]]]), np.array([[target[1]]]))[0, 0]
        )
    out = Path(out)
    use_ffmpeg = animation.writers.is_available("ffmpeg") and out.suffix.lower() != ".gif"
    out = out.with_suffix(".mp4" if use_ffmpeg else ".gif")
    fps = 1.0 / hold
    writer = (
        animation.FFMpegWriter(fps=fps, codec="libx264", extra_args=["-pix_fmt", "yuv420p"])
        if use_ffmpeg
        else animation.PillowWriter(fps=fps)
    )
    fig = plt.figure(figsize=FIGSIZE, dpi=DPI, facecolor=SURFACE)
    ax = fig.add_axes([0.03, 0.17, 0.94, 0.70])
    cax = fig.add_axes([0.2, 0.085, 0.6, 0.018])
    cb = fig.colorbar(ScalarMappable(norm=BoundaryNorm(LEVELS, cmap.N), cmap=cmap), cax=cax, orientation="horizontal",
                      ticks=[-2, 0, 2])  # fmt: skip
    cb.ax.set_xticklabels([f"{names[loser]} first by 2 s", "level", f"{names[winner]} first by 2 s"])
    cb.ax.tick_params(labelsize=9, colors=MUTED)
    cb.outline.set_edgecolor(GRID)
    cax.set_visible(False)
    texts = []

    def draw(stage: str, f: int) -> None:
        ax.clear()
        for t in texts:
            t.remove()
        texts.clear()
        ax.set_facecolor(SURFACE)
        shaded = stage != "before"
        cax.set_visible(shaded)
        at = vel[vel["frame"] == f].copy()
        if stage == "model":
            at.loc[at["column_id"] == e["enough_player"], ["x", "y"]] = moved
        if shaded:
            mg = margin_grid(at, loser, winner, gx, gy)
            ax.contourf(gx, gy, mg, levels=LEVELS, cmap=cmap, alpha=0.6, zorder=0)
            ax.contour(gx, gy, mg, levels=[0.0], colors=INK, linewidths=1.0, zorder=2)
        _pitch(ax, *m.pitch_dimensions)
        corners = tr.loc[f, [f"camera_{c}_{a}" for c in CORNERS for a in ("x", "y")]].to_numpy(dtype=float)
        if np.isfinite(corners).all():
            ax.add_patch(
                Polygon(
                    corners.reshape(4, 2), closed=True, fill=False, ec=MUTED, lw=1.2, ls=(0, (2, 2)), zorder=3
                )
            )
        if shaded:
            ax.add_patch(
                Circle(tuple(target), RADIUS, fill=False, color=MUTED, lw=1.0, ls=(0, (4, 3)), zorder=3)
            )
            ax.scatter(*target, marker="x", s=150, color=INK, lw=2.4, zorder=6)
        ball = tr.loc[release:f, ["ball_x", "ball_y", "ball_detected"]]
        seen = ball[
            ball["ball_detected"].fillna(False).astype(bool) & ball[["ball_x", "ball_y"]].notna().all(axis=1)
        ]
        if len(seen):
            ax.plot(seen["ball_x"], seen["ball_y"], color=INK, lw=1.4, alpha=0.7, zorder=4)
            last = seen.iloc[-1]
            now_seen = seen.index[-1] == f
            ax.scatter(last["ball_x"], last["ball_y"], s=60, facecolor=INK if now_seen else SURFACE, edgecolor=INK,
                       lw=1.6, zorder=9)  # fmt: skip
        for team, colour in ((winner, BLUE), (loser, ORANGE)):
            rows = at[(at["team_id"] == team) & at["x"].between(*xlim) & at["y"].between(*ylim)]
            det = rows["detected"].fillna(False).to_numpy(dtype=bool)
            if stage == "model":
                det = det | (rows["column_id"] == e["enough_player"]).to_numpy()
            ax.scatter(rows["x"], rows["y"], s=170, facecolor=np.where(det, colour, SURFACE), edgecolor=colour,
                       lw=2.2, zorder=7)  # fmt: skip
            for p, filled in zip(rows.itertuples(), det):
                ax.text(p.x, p.y, p.column_id.split("_")[-1], ha="center", va="center", fontsize=7.5,
                        color="white" if filled else colour, fontweight="bold", zorder=8)  # fmt: skip
                if np.isfinite(p.vx):
                    ax.annotate("", (p.x + p.vx, p.y + p.vy), (p.x, p.y), zorder=8,
                                arrowprops={"arrowstyle": "-|>", "color": colour, "lw": 1.6, "mutation_scale": 12})  # fmt: skip
        if stage == "model":
            ax.scatter(
                *ghost, s=170, facecolor="none", edgecolor=ORANGE, lw=1.6, linestyle=(0, (2, 2)), zorder=7
            )
            ax.annotate("", tuple(moved), tuple(ghost), zorder=8,
                        arrowprops={"arrowstyle": "-|>", "color": INK, "lw": 1.6, "linestyle": "--"})  # fmt: skip
            mid = (ghost + moved) / 2
            ax.text(mid[0], mid[1] + 1.2, f"{float(e['metres_short']):.1f} m", ha="center", fontsize=11, color=INK,
                    fontweight="bold", zorder=9)  # fmt: skip
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        clock = tr.loc[f, "clock"]
        head = f"{names[m.home_team_id]} v {names[m.away_team_id]}, match clock {clock}"
        if stage == "model":
            sub, line = "model: one change", "The model now has the race level."
        elif stage == "before":
            sub, line = "As recorded", "Drop zone not yet in view"
        elif stage == "pickup":
            sub, line = "As recorded", f"{names[winner]} won the ball"
        else:
            sub, line = "As recorded", "Drop zone in view" if stage == "anchor" else ""
        texts.append(fig.text(0.03, 0.955, head, fontsize=13, color=INK))
        texts.append(fig.text(0.03, 0.918, sub, fontsize=13, color=INK if stage == "model" else MUTED,
                              fontweight="bold" if stage == "model" else "normal"))  # fmt: skip
        texts.append(fig.text(0.03, 0.885, line, fontsize=11.5, color=INK))
        if shaded:
            texts.append(fig.text(0.03, 0.135, caption, fontsize=11.5, color=INK))
        texts.append(fig.text(0.97, 0.02, "dots: shirt numbers; hollow: position estimated, off camera; arrows: one "
                              "second of movement; dashed outline: camera view", fontsize=8, color=MUTED, ha="right"))  # fmt: skip

    frames = 0
    with writer.saving(fig, str(out), dpi=DPI):
        for stage, f, repeats in steps:
            draw(stage, f)
            for _ in range(repeats):
                writer.grab_frame(facecolor=SURFACE)
                frames += 1
    plt.close(fig)
    return {"file": str(out), "frames": frames, "seconds": frames * hold, "verdict": d["verdict"],
            "enough_type": e["enough_type"], "model part": bool(model_part),
            "margin at the pickup point after the change": level_margin if model_part else None}  # fmt: skip
