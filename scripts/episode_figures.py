"""Seeded episode figures for bug finding (step 1).

Draw, without replacement, with numpy default_rng(SEED): 6 from all main pairs, then 3 from
main pairs with gap >= the 95th percentile of main-pair gaps, then 2 from T7 main pairs.
Each figure has two panels, release frame and pickup frame: the camera view, the ball path
through the window, players within 15 m of the pickup point with detection flags, and the
pickup point from tracking and from the event.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Polygon, Rectangle

from looseball import episodes, io, paths, tracking

SEED = 20261027
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
RELEASING, OTHER = "#2a78d6", "#eb6834"
CORNERS = ("top_left", "top_right", "bottom_right", "bottom_left")


def draw_set(main):
    rng = np.random.default_rng(SEED)
    main = main.sort_values(["match_id", "seq_i"]).reset_index(drop=True)
    chosen = list(rng.choice(len(main), 6, replace=False))
    groups = ["general"] * 6
    cut = np.quantile(main["gap"], 0.95)
    tail = [i for i in np.flatnonzero(main["gap"] >= cut) if i not in chosen]
    chosen += list(rng.choice(tail, 3, replace=False))
    groups += ["gap tail"] * 3
    t7 = [i for i in np.flatnonzero(main["trigger"] == "T7") if i not in chosen]
    chosen += list(rng.choice(t7, 2, replace=False))
    groups += ["T7"] * 2
    return main.loc[chosen].assign(group=groups), cut


def pitch(ax, length, width):
    hl, hw = length / 2, width / 2
    kw = {"color": GRID, "linewidth": 1, "zorder": 0}
    ax.add_patch(Rectangle((-hl, -hw), length, width, fill=False, **kw))
    ax.plot([0, 0], [-hw, hw], **kw)
    ax.add_patch(Circle((0, 0), 9.15, fill=False, **kw))
    for s in (-1, 1):
        ax.add_patch(Rectangle((s * hl - (16.5 if s > 0 else 0), -20.16), 16.5, 40.32, fill=False, **kw))


def panel(ax, ep, fr, pl, team_of, label, frame, meta):
    pitch(ax, meta["pitch_length"], meta["pitch_width"])
    row = fr.loc[frame]
    corners = [
        (row[f"image_corners_projection.x_{c}"], row[f"image_corners_projection.y_{c}"]) for c in CORNERS
    ]
    if not np.isnan(np.array(corners, dtype=float)).any():
        ax.add_patch(Polygon(corners, closed=True, facecolor=GRID, alpha=0.55, edgecolor="none", zorder=0))

    px, py = ep["pickup_x"], ep["pickup_y"]
    for radius, style in ((15, "-"), (10, (0, (3, 3)))):
        ax.add_patch(
            Circle((px, py), radius, fill=False, color=MUTED, linewidth=0.8, linestyle=style, zorder=1)
        )

    w = fr.loc[ep["release_frame"] : ep["pickup_frame"]]
    ax.plot(w["ball_data.x"], w["ball_data.y"], color=MUTED, linewidth=1, zorder=2)
    det = w["ball_data.is_detected"].fillna(False).astype(bool)
    ax.scatter(w.loc[det, "ball_data.x"], w.loc[det, "ball_data.y"], s=9, color=INK, zorder=3)
    ax.scatter(
        w.loc[~det, "ball_data.x"],
        w.loc[~det, "ball_data.y"],
        s=9,
        facecolor=SURFACE,
        edgecolor=INK,
        linewidth=0.6,
        zorder=3,
    )
    ax.scatter([row["ball_data.x"]], [row["ball_data.y"]], s=40, color=INK, marker="o", zorder=4)

    p = pl[pl["frame"] == frame].copy()
    p["team"] = team_of.reindex(p["player_id"]).to_numpy()
    p["d"] = np.hypot(p["x"] - px, p["y"] - py)
    far = p[p["d"] > 15]
    ax.scatter(far["x"], far["y"], s=12, color=GRID, zorder=2)
    near = p[p["d"] <= 15]
    for _, q in near.iterrows():
        color = RELEASING if q["team"] == ep["team_id_i"] else OTHER
        filled = bool(q["is_detected"])
        ax.scatter(
            q["x"],
            q["y"],
            s=70,
            facecolor=color if filled else SURFACE,
            edgecolor=color,
            linewidth=1.6,
            zorder=5,
        )
        tag = (
            "i"
            if q["player_id"] == ep["player_id_i"]
            else "i+1"
            if q["player_id"] == ep["player_id_next"]
            else ""
        )
        if tag:
            ax.annotate(
                tag,
                (q["x"], q["y"]),
                xytext=(6, 6),
                textcoords="offset points",
                fontsize=8,
                color=INK,
                zorder=6,
            )

    ax.scatter([px], [py], marker="x", s=70, color=INK, linewidth=1.6, zorder=6)
    ax.scatter(
        [ep["pickup_event_x"]], [ep["pickup_event_y"]], marker="+", s=110, color=INK, linewidth=1.2, zorder=6
    )
    n15 = len(near)
    k15 = int(near["is_detected"].fillna(False).astype(bool).sum())
    ax.set_title(
        f"{label} frame {frame} ({fr.loc[frame, 'frame_class']}): {k15} of {n15} within 15 m detected",
        fontsize=9.5,
        color=INK,
        loc="left",
    )

    xs = [px, ep["pickup_event_x"], *w["ball_data.x"].dropna()]
    ys = [py, ep["pickup_event_y"], *w["ball_data.y"].dropna()]
    pad = 18
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_aspect("equal")
    ax.set_facecolor(SURFACE)
    ax.tick_params(colors=MUTED, labelsize=7.5)
    for s in ax.spines.values():
        s.set_color(GRID)


def figure(ep, k, n_total):
    m = int(ep["match_id"])
    fr = tracking.load_frames(m).set_index("frame", drop=False)
    pl = tracking.load_players(m)
    meta = io.load_metadata(m)
    team_of = io.load_roster(m).set_index("id")["team_id"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.4), facecolor=SURFACE)
    panel(axes[0], ep, fr, pl, team_of, "release", int(ep["release_frame"]), meta)
    panel(axes[1], ep, fr, pl, team_of, "pickup", int(ep["pickup_frame"]), meta)
    fig.suptitle(
        f"Episode {k} of {n_total} (seed {SEED}, draw: {ep['group']}). Match {m}, possessions {ep['seq_i']} to {ep['seq_next']}. "
        f"{episodes.TRIGGER_LABELS[ep['trigger']]}, resolution {ep['resolution']}, {ep['continuity']}.\n"
        f"Gap {ep['gap']} frames ({ep['gap'] / paths.FPS:.1f} s); ball detected on {ep['window_ball_detected']} of "
        f"{ep['window_frames']} window frames; max detected z {ep['max_ball_z_detected']:.1f} m; "
        f"pickup point tracking vs event {ep['pickup_disagreement_m']:.1f} m.",
        fontsize=10,
        color=INK,
        x=0.01,
        ha="left",
    )
    handles = [
        Line2D(
            [], [], marker="o", linestyle="", markersize=8, color=RELEASING, label="releasing team, detected"
        ),
        Line2D(
            [],
            [],
            marker="o",
            linestyle="",
            markersize=8,
            markerfacecolor=SURFACE,
            markeredgecolor=RELEASING,
            label="releasing team, not detected",
        ),
        Line2D([], [], marker="o", linestyle="", markersize=8, color=OTHER, label="other team, detected"),
        Line2D(
            [],
            [],
            marker="o",
            linestyle="",
            markersize=8,
            markerfacecolor=SURFACE,
            markeredgecolor=OTHER,
            label="other team, not detected",
        ),
        Line2D(
            [],
            [],
            marker="o",
            linestyle="-",
            markersize=4,
            color=INK,
            label="ball path, detected frames filled",
        ),
        Line2D([], [], marker="x", linestyle="", markersize=8, color=INK, label="pickup point, tracking"),
        Line2D(
            [], [], marker="+", linestyle="", markersize=10, color=INK, label="pickup point, event (rotated)"
        ),
        Line2D(
            [],
            [],
            marker="s",
            linestyle="",
            markersize=10,
            color=GRID,
            label="camera view; grey dots: players beyond 15 m",
        ),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=8, frameon=False, labelcolor=MUTED)
    fig.tight_layout(rect=(0, 0.08, 1, 0.9))
    name = f"episode_seed{SEED}_{k:02d}_{ep['group'].replace(' ', '_')}_{m}_{ep['seq_i']}.png"
    fig.savefig(paths.FIGURES / name, dpi=130, facecolor=SURFACE)
    plt.close(fig)
    return name


def main():
    ep = episodes.all_episodes()
    drawn, cut = draw_set(ep[ep["main"]])
    print(f"seed {SEED}; gap tail cut (95th percentile of main-pair gaps): {cut:.1f} frames\n")
    rows = []
    for k, (_, e) in enumerate(drawn.iterrows(), start=1):
        name = figure(e, k, len(drawn))
        rows.append(
            {
                "figure": k,
                "draw": e["group"],
                "match_id": e["match_id"],
                "seq_i": e["seq_i"],
                "trigger": e["trigger"],
                "resolution": e["resolution"],
                "gap": e["gap"],
                "file": f"audit/figures/{name}",
            }
        )
    print(pd.DataFrame(rows).to_markdown(index=False))


if __name__ == "__main__":
    main()
