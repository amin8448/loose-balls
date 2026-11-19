"""looseball animate (step 3, 3h): one lost ball as recorded, then, for a move ball, the one
change under the model. Not part of looseball reproduce and not byte-checked.

Part one, "as recorded", from the release frame (or `start_before_anchor` seconds before the
anchor) to the pickup frame, each data frame held for `hold` seconds; no position is interpolated.
Before the anchor: both teams as dots with velocity arrows (one second of current movement), hollow
when not detected, the camera view outlined, the ball with its trail (hollow at its last detected
position when not detected); the label is "drop zone not yet in view" on frames where the pickup
point is outside the camera view and "before the last touch" on the others; no shading and no
pickup marker. At the anchor (held 1.5 s): the shading, the pickup marker, the 15 m race circle and
one caption line. From the anchor to the pickup: recorded positions, shading recomputed on each
frame. The pickup frame is held 1 s with the team that won the ball named.

Shading (revision of 2026-11-18, a presentation choice that differs from Figure 1): each team's best
dynamic reach time to every point from its players in the race (within 15 m of the pickup point on
the anchor frame; on later frames the same players at their recorded positions; a team with nobody
in the race gets the empty-team time everywhere), frozen reach model, as the winning team's margin
clipped at 2 s, drawn only inside the 15 m race circle. Outside the circle: dots and arrows only.

Part two, labelled "model: one change" throughout, only for enough_type move: the anchor frame
frozen, the best-placed player as a ghost at his recorded spot and at the moved spot (metres_short
along the line from his drifted position to the pickup point), an arrow with the distance, the
shading recomputed with the change, and the label that the model now has the race level; held
3 s. For enough_type no_player_in_race, part one ends with the pickup frame held 2 s and a label that
the losing team had no player within 15 m. No recorded track is replayed next to a model-driven
player.

In part two the moved player is drawn as an outlined ring under the other players, with his shirt
number beside it, so he never hides another player's number; that number and the distance label
are placed clear of every player dot, the ghost and the pickup marker; the panel is extended where needed so the whole 15 m race circle shows. Players are
labelled by shirt number only. Output: mp4 through ffmpeg when available, GIF
otherwise; optionally a contact sheet (first frame, anchor, pickup, and the model or closing frame).
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
from PIL import Image

from looseball import decompose, expectations, find_episodes, reach_times
from looseball.adapters.skillcorner import load_match
from looseball.enough import enough
from looseball.episodes import _in_view
from looseball.figures import BLUE, GRID, INK, MUTED, NEUTRAL, ORANGE, SURFACE, _pitch
from looseball.race import RADIUS, REACTION, ReachModel
from looseball.schema import CORNERS, FPS
from looseball.velocities import tracking_velocities

HOLD = 0.25  # seconds per data frame
ANCHOR_HOLD, PICKUP_HOLD, MODEL_HOLD, CLOSING_HOLD = 1.5, 1.0, 3.0, 2.0
MARGIN_CLIP = 2.0
LEVELS = np.arange(-2.0, 2.01, 0.25)
GRID_POINTS = 160
PAD, AROUND_PICKUP = 4.0, 16.0  # metres
FIGSIZE, DPI = (10.0, 8.4), 100  # 1000 x 840 pixels, even for the mp4 encoder
DOT_SIZE, DOT_EDGE, NUMBER_SIZE = 620, 2.2, 12  # points^2, points, points
DOT_RADIUS_PX = (np.sqrt(DOT_SIZE) + DOT_EDGE) / 2 * DPI / 72
MARKER_SIZE = 150  # points^2, the pickup marker
MARKER_RADIUS_PX = (np.sqrt(MARKER_SIZE) + 2.4) / 2 * DPI / 72
CIRCLE_MARGIN = 1.0  # metres of panel kept beyond the race circle
MOVED_RING = 3.0  # points, the moved player's ring in the model frame
LABEL_GAP = 3.0  # pixels between the distance label and any dot or the pickup marker
LABEL_RINGS = (0, 18, 28, 40, 54, 70, 88, 110, 135, 165)  # pixels from the arrow's midpoint
CAMERA_COLUMNS = [f"camera_{c}_{a}" for c in CORNERS for a in ("x", "y")]


def schedule(start: int, anchor: int, pickup: int, ending: str | None, hold: float = HOLD) -> list:
    """The animation as (stage, data frame, repeats). Stages: before, anchor, after, pickup, then
    "model" (ending "model") or "closing" (ending "closing"), or nothing (ending None)."""

    def n(seconds: float) -> int:
        return max(1, round(seconds / hold))

    steps = [("before", f, 1) for f in range(start, anchor)]
    steps.append(("anchor", anchor, n(ANCHOR_HOLD)))
    steps += [("after", f, 1) for f in range(anchor + 1, pickup)]
    if pickup > anchor:
        steps.append(("pickup", pickup, n(PICKUP_HOLD)))
    if ending == "model":
        steps.append(("model", anchor, n(MODEL_HOLD)))
    elif ending == "closing":
        steps.append(("closing", pickup, n(CLOSING_HOLD)))
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


def _extent(tracking: pd.DataFrame, start: int, ep, pitch) -> tuple:
    path = tracking.loc[start : int(ep.pickup_frame), ["ball_x", "ball_y"]].to_numpy(dtype=float)
    path = path[np.isfinite(path).all(axis=1)]
    px, py = float(ep.pickup_x), float(ep.pickup_y)
    xs = np.r_[path[:, 0], px - AROUND_PICKUP, px + AROUND_PICKUP]
    ys = np.r_[path[:, 1], py - AROUND_PICKUP, py + AROUND_PICKUP]
    length, width = pitch
    xlim = (max(xs.min() - PAD, -length / 2 - 2), min(xs.max() + PAD, length / 2 + 2))
    ylim = (max(ys.min() - PAD, -width / 2 - 2), min(ys.max() + PAD, width / 2 + 2))
    # never cut the race circle: extend the panel past the pitch cut where the circle needs it
    reach = RADIUS + CIRCLE_MARGIN
    xlim = (min(xlim[0], px - reach), max(xlim[1], px + reach))
    ylim = (min(ylim[0], py - reach), max(ylim[1], py + reach))
    return xlim, ylim


def _rect_circle_gap(box, cx: float, cy: float, r: float) -> float:
    """Pixels between a rectangle (a matplotlib Bbox) and a circle; negative when they overlap."""
    dx = max(box.x0 - cx, 0.0, cx - box.x1)
    dy = max(box.y0 - cy, 0.0, cy - box.y1)
    return float(np.hypot(dx, dy)) - r


def place_label(fig, ax, label, around, obstacles, gap: float = LABEL_GAP) -> float:
    """Move `label` (a text in data coordinates) to the nearest spot around `around` that is at least
    `gap` pixels clear of every obstacle (x, y, radius in pixels) and inside the axes; the spots are
    tried on rings of growing radius. Returns the clearance in pixels of the spot used (the best
    found when none is fully clear)."""
    ax.apply_aspect()
    renderer = fig.canvas.get_renderer()
    to_px, to_data = ax.transData.transform, ax.transData.inverted().transform
    centre = to_px(np.asarray(around, float))
    obs = [(*to_px((x, y)), r) for x, y, r in obstacles]
    frame = ax.get_window_extent(renderer)
    best, best_clear = None, -np.inf
    for radius in LABEL_RINGS:
        for angle in np.linspace(0, 2 * np.pi, 1 if radius == 0 else 24, endpoint=False):
            spot = centre + radius * np.array([np.cos(angle), np.sin(angle)])
            label.set_position(to_data(spot))
            box = label.get_window_extent(renderer)
            if box.x0 < frame.x0 or box.x1 > frame.x1 or box.y0 < frame.y0 or box.y1 > frame.y1:
                continue
            clear = min((_rect_circle_gap(box, cx, cy, r) for cx, cy, r in obs), default=np.inf)
            if clear >= gap:
                return clear
            if clear > best_clear:
                best, best_clear = spot, clear
    if best is not None:
        label.set_position(to_data(best))
    return best_clear


def drop_zone_in_view(tracking: pd.DataFrame, frame: int, target) -> bool:
    """Whether the pickup point lies inside the camera polygon on `frame` (the anchor rule)."""
    corners = tracking.loc[frame, CAMERA_COLUMNS].to_numpy(dtype=float).reshape(4, 2)
    return _in_view(corners, float(target[0]), float(target[1]))


def margin_grid(players: pd.DataFrame, loser: int, winner: int, gx, gy, target=None) -> np.ndarray:
    """The winning team's margin (loser's best dynamic reach time minus winner's), clipped at 2 s,
    from the players given (x, y, vx, vy, team_id), frozen reach model; a team with nobody gets the
    empty-team time. With `target`, points farther than the race radius from it are NaN."""
    model = ReachModel()
    grid = np.column_stack([gx.ravel(), gy.ravel()])
    empty = model.empty_team_time(RADIUS)

    def best(team):
        rows = players[players["team_id"] == team]
        times = [
            model.tti(np.array([p.x, p.y]), grid, np.nan_to_num(np.array([p.vx, p.vy])))
            for p in rows.itertuples()
        ]
        return np.min(times, axis=0) if times else np.full(len(grid), empty)

    margin = np.clip(best(loser) - best(winner), -MARGIN_CLIP, MARGIN_CLIP).reshape(gx.shape)
    if target is not None:
        margin[np.hypot(gx - target[0], gy - target[1]) > RADIUS] = np.nan
    return margin


def moved_spot(enough_row, race: pd.DataFrame, target) -> tuple:
    """The best-placed player's recorded and moved positions (move balls)."""
    p = race[race["column_id"] == enough_row["enough_player"]].iloc[0]
    pos, vel = np.array([p.x, p.y], float), np.nan_to_num(np.array([p.vx, p.vy], float))
    drift = np.asarray(target, float) - (pos + REACTION * vel)
    return pos, pos + float(enough_row["metres_short"]) * drift / np.hypot(*drift)


def _sheet(images: list, path: Path) -> None:
    """Contact sheet: the captured frames at half size, two per row."""
    tiles = [Image.fromarray(im).convert("RGB").resize((im.shape[1] // 2, im.shape[0] // 2)) for im in images]
    w, h = tiles[0].size
    rows = (len(tiles) + 1) // 2
    sheet = Image.new("RGB", (2 * w, rows * h), "white")
    for k, t in enumerate(tiles):
        sheet.paste(t, ((k % 2) * w, (k // 2) * h))
    sheet.save(path)


def animate(data, match_id: int, seq_i: int, out, hold: float = HOLD, start_before_anchor: float | None = None,
            sheet=None) -> dict:  # fmt: skip
    """Write the animation of one lost ball to `out` (.mp4 through ffmpeg when available, else
    .gif), and a contact sheet to `sheet` when given."""
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
    start = (
        release if start_before_anchor is None else max(release, anchor - round(start_before_anchor * FPS))
    )
    target = np.array([ep.pickup_x, ep.pickup_y], float)
    ending = {"move": "model", "no_player_in_race": "closing"}.get(e["enough_type"])
    steps = schedule(start, anchor, pickup, ending, hold)
    names = m.team_names
    team_of = m.players.set_index("column_id")["team_id"]
    vel = vel[vel["frame"].between(start, pickup) & vel["column_id"].isin(team_of.index)].copy()
    vel["team_id"] = team_of.reindex(vel["column_id"]).to_numpy()
    in_race = set(race.loc[~race["empty_team"].astype(bool), "column_id"])
    tr = m.tracking
    xlim, ylim = _extent(tr, start, ep, m.pitch_dimensions)
    gx, gy = np.meshgrid(np.linspace(*xlim, GRID_POINTS), np.linspace(*ylim, GRID_POINTS))
    cmap = LinearSegmentedColormap.from_list("margin", [ORANGE, NEUTRAL, BLUE])
    caption = (
        f"{names[loser]}: {100 * d['p_static_loser']:.1f}% from position, {100 * d['p_dynamic_loser']:.1f}% with "
        f"movement: lost on {d['verdict']}"
    )
    level_margin = None
    if ending == "model":
        ghost, moved = moved_spot(e, race, target)
        level = vel[(vel["frame"] == anchor) & vel["column_id"].isin(in_race)].copy()
        level.loc[level["column_id"] == e["enough_player"], ["x", "y"]] = moved
        level_margin = float(
            margin_grid(level, loser, winner, np.array([[target[0]]]), np.array([[target[1]]]))[0, 0]
        )
    before_in_view = sum(drop_zone_in_view(tr, f, target) for f in range(start, anchor))
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
    cb.ax.set_title("shading inside the 15 m race circle: which team gets to each point first", fontsize=9,
                    color=MUTED)  # fmt: skip
    cax.set_visible(False)
    texts, clearance, number_clearance = [], [], []

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
            mg = margin_grid(at[at["column_id"].isin(in_race)], loser, winner, gx, gy, target)
            ax.contourf(gx, gy, mg, levels=LEVELS, cmap=cmap, alpha=0.6, zorder=0)
            ax.contour(gx, gy, mg, levels=[0.0], colors=INK, linewidths=1.0, zorder=2)
        _pitch(ax, *m.pitch_dimensions)
        corners = tr.loc[f, CAMERA_COLUMNS].to_numpy(dtype=float)
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
            ax.scatter(*target, marker="x", s=MARKER_SIZE, color=INK, lw=2.4, zorder=6)
        ball = tr.loc[start:f, ["ball_x", "ball_y", "ball_detected"]]
        seen = ball[
            ball["ball_detected"].fillna(False).astype(bool) & ball[["ball_x", "ball_y"]].notna().all(axis=1)
        ]
        if len(seen):
            ax.plot(seen["ball_x"], seen["ball_y"], color=INK, lw=1.4, alpha=0.7, zorder=4)
            last = seen.iloc[-1]
            now_seen = seen.index[-1] == f
            ax.scatter(last["ball_x"], last["ball_y"], s=60, facecolor=INK if now_seen else SURFACE, edgecolor=INK,
                       lw=1.6, zorder=9)  # fmt: skip
        dots = []
        for team, colour in ((winner, BLUE), (loser, ORANGE)):
            rows = at[(at["team_id"] == team) & at["x"].between(*xlim) & at["y"].between(*ylim)]
            for p in rows.itertuples():
                if np.isfinite(p.vx):
                    ax.annotate("", (p.x + p.vx, p.y + p.vy), (p.x, p.y), zorder=7,
                                arrowprops={"arrowstyle": "-|>", "color": colour, "lw": 1.6, "mutation_scale": 12})  # fmt: skip
            if stage == "model":  # the moved player is drawn as a ring with his number beside it
                rows = rows[rows["column_id"] != e["enough_player"]]
            dots += [(x, y, DOT_RADIUS_PX) for x, y in zip(rows["x"], rows["y"])]
            det = rows["detected"].fillna(False).to_numpy(dtype=bool)
            ax.scatter(rows["x"], rows["y"], s=DOT_SIZE, facecolor=np.where(det, colour, SURFACE), edgecolor=colour,
                       lw=DOT_EDGE, zorder=8)  # fmt: skip
            for p, filled in zip(rows.itertuples(), det):
                ax.text(p.x, p.y, p.column_id.split("_")[-1], ha="center", va="center_baseline", fontsize=NUMBER_SIZE,
                        color="white" if filled else colour, fontweight="bold", zorder=9)  # fmt: skip
        if stage == "model":
            ax.scatter(*moved, s=DOT_SIZE, facecolor="none", edgecolor=ORANGE, lw=MOVED_RING, zorder=7.5)
            ax.scatter(
                *ghost,
                s=DOT_SIZE,
                facecolor="none",
                edgecolor=ORANGE,
                lw=1.6,
                linestyle=(0, (2, 2)),
                zorder=8,
            )
            ax.annotate("", tuple(moved), tuple(ghost), zorder=10,
                        arrowprops={"arrowstyle": "-|>", "color": INK, "lw": 1.8, "linestyle": "--"})  # fmt: skip
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal")
        if stage == "model":
            obstacles = [*dots, (*moved, DOT_RADIUS_PX), (*ghost, DOT_RADIUS_PX), (*target, MARKER_RADIUS_PX)]
            number = ax.text(*moved, str(e["enough_player"]).split("_")[-1], ha="center", va="center",
                             fontsize=NUMBER_SIZE, color=ORANGE, fontweight="bold", zorder=10)  # fmt: skip
            number_clearance.append(place_label(fig, ax, number, moved, obstacles))
            box = number.get_window_extent(fig.canvas.get_renderer())
            centre = ax.transData.inverted().transform(((box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2))
            mid = (ghost + moved) / 2
            label = ax.text(mid[0], mid[1], f"{float(e['metres_short']):.1f} m", ha="center", va="center", fontsize=12,
                            color=INK, fontweight="bold", zorder=10)  # fmt: skip
            number_obstacle = (*centre, float(np.hypot(box.width, box.height)) / 2)
            clearance.append(place_label(fig, ax, label, mid, [*obstacles, number_obstacle]))
        ax.set_xticks([])
        ax.set_yticks([])
        head = f"{names[m.home_team_id]} v {names[m.away_team_id]}, match clock {tr.loc[f, 'clock']}"
        if stage == "model":
            sub, line = "model: one change", "The model now has the race level."
        elif stage == "before":
            in_view = drop_zone_in_view(tr, f, target)
            sub, line = "As recorded", "Before the last touch" if in_view else "Drop zone not yet in view"
        elif stage == "pickup":
            sub, line = "As recorded", f"{names[winner]} won the ball"
        elif stage == "closing":
            sub, line = "As recorded", f"{names[loser]} had no player within 15 m of where the ball was won"
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

    frames, captured, firsts = 0, [], {"first", "anchor", "pickup", "model", "closing"}
    with writer.saving(fig, str(out), dpi=DPI):
        for k, (stage, f, repeats) in enumerate(steps):
            draw(stage, f)
            label = "first" if k == 0 else stage
            if sheet is not None and label in firsts:
                fig.canvas.draw()
                captured.append(np.asarray(fig.canvas.buffer_rgba()).copy())
                firsts.discard(label)
            for _ in range(repeats):
                writer.grab_frame(facecolor=SURFACE)
                frames += 1
    plt.close(fig)
    if sheet is not None:
        _sheet(captured, Path(sheet))
    return {"file": str(out), "frames": frames, "seconds": frames * hold, "verdict": d["verdict"],
            "enough_type": e["enough_type"], "ending": ending, "start frame": start,
            "frames before the anchor": anchor - start, "frames before the anchor with the drop zone in view": before_in_view,
            "margin at the pickup point after the change": level_margin,
            "label clearance px": min(clearance) if clearance else None,
            "moved number clearance px": min(number_clearance) if number_clearance else None}  # fmt: skip
