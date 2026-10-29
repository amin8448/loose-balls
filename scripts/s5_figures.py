"""S5 figures (bug check): four seeded episode figures and the team deficit figure.

Episode figure: two panels at the last-leg anchor. Left, static: each team's best reach time to
every point (velocities set to zero), as contours. Right, dynamic: the same with smoothed
velocities, drawn as arrows covering one second of motion. Players in the race are filled when
detected; the pickup point, the 15 m radius and the camera view are marked. The title carries
p_static and p_dynamic of the releasing team and the losing team's three deficit shares.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from episode_figures import GRID, INK, MUTED, OTHER, RELEASING, SURFACE, pitch
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Polygon

from looseball_research import decompose, episodes, io, paths, race, tracking, velocities

SEED = 20261028
LEVELS = [1.0, 1.5, 2.0, 2.5, 3.0]
HALF = 22.0  # metres shown around the pickup point


def team_field(model, players: pd.DataFrame, grid: np.ndarray, dynamic: bool) -> np.ndarray | None:
    if players.empty:
        return None
    times = []
    for p in players.itertuples():
        vel = np.array([p.vx, p.vy]) if dynamic and not np.isnan(p.vx) else np.zeros(2)
        times.append(model.tti(np.array([p.x, p.y]), grid, vel))
    return np.min(times, axis=0)


def episode_figure(e: pd.Series, k: int, team_names: dict) -> str:
    m = int(e["match_id"])
    vel = velocities.match_velocities(m)
    fr = tracking.load_frames(m).set_index("frame", drop=False)
    meta = io.load_metadata(m)
    roster = io.load_roster(m)
    team_of = roster.set_index("id")["team_id"]
    gk = set(roster.loc[roster["player_role.acronym"] == "GK", "id"])
    model = race.ReachModel()
    anchor, target = int(e["anchor_frame"]), (float(e["pickup_x"]), float(e["pickup_y"]))
    at = vel[vel["frame"] == anchor]
    players = race.race_players(at, target, e["team_id_i"], team_of, gk, race.RADIUS, model)
    rest = at[~at["player_id"].isin(players["player_id"])]
    gx, gy = np.meshgrid(
        np.linspace(target[0] - HALF, target[0] + HALF, 89),
        np.linspace(target[1] - HALF, target[1] + HALF, 89),
    )
    grid = np.column_stack([gx.ravel(), gy.ravel()])
    row = fr.loc[anchor]
    corners = [
        (row[f"image_corners_projection.x_{c}"], row[f"image_corners_projection.y_{c}"])
        for c in episodes.VIEW_CORNERS
    ]

    fig, axes = plt.subplots(1, 2, figsize=(14, 7.2), facecolor=SURFACE)
    for ax, dynamic in zip(axes, (False, True)):
        ax.set_facecolor(SURFACE)
        pitch(ax, meta["pitch_length"], meta["pitch_width"])
        if not np.isnan(np.array(corners, dtype=float)).any():
            ax.add_patch(Polygon(corners, closed=True, facecolor=GRID, alpha=0.5, edgecolor="none", zorder=0))
        for side, color in (("releasing", RELEASING), ("other", OTHER)):
            f = team_field(model, players[players["side"] == side], grid, dynamic)
            if f is not None:
                cs = ax.contour(
                    gx, gy, f.reshape(gx.shape), levels=LEVELS, colors=color, linewidths=1.0, zorder=2
                )
                ax.clabel(cs, fmt="%.1f s", fontsize=7)
        ax.scatter(rest["x"], rest["y"], s=12, color=GRID, zorder=3)
        for p in players.itertuples():
            color = RELEASING if p.side == "releasing" else OTHER
            ax.scatter(p.x, p.y, s=70, facecolor=color if p.is_detected else SURFACE, edgecolor=color,
                       linewidth=1.6, marker="s" if p.is_gk else "o", zorder=5)  # fmt: skip
            if dynamic and not np.isnan(p.vx):
                ax.annotate("", (p.x + p.vx, p.y + p.vy), (p.x, p.y), zorder=6,
                            arrowprops={"arrowstyle": "->", "color": color, "lw": 1.3})  # fmt: skip
            if p.player_id == e["player_id_next"]:
                ax.annotate(
                    "winner", (p.x, p.y), xytext=(6, -12), textcoords="offset points", fontsize=8, color=INK
                )
        ax.add_patch(
            Circle(target, race.RADIUS, fill=False, color=MUTED, linewidth=0.8, linestyle=(0, (3, 3)))
        )
        ax.scatter([row["ball_data.x"]], [row["ball_data.y"]], s=40, color=INK, zorder=7)
        ax.scatter([target[0]], [target[1]], marker="x", s=90, color=INK, linewidth=1.8, zorder=7)
        ax.set_xlim(target[0] - HALF, target[0] + HALF)
        ax.set_ylim(target[1] - HALF, target[1] + HALF)
        ax.set_aspect("equal")
        ax.tick_params(colors=MUTED, labelsize=7.5)
        for s in ax.spines.values():
            s.set_color(GRID)
        ax.set_title(
            "static: positions only, velocities set to zero" if not dynamic else "dynamic: smoothed velocities (arrows: 1 s)",
            fontsize=9.5, color=INK, loc="left",
        )  # fmt: skip
    loser = team_names[e["losing_team"]]
    fig.suptitle(
        f"S5 episode {k} of 4 (seed {SEED}, bug check). Match {m}, possessions {e['seq_i']} to {e['seq_i'] + 1}, "
        f"{episodes.TRIGGER_LABELS[e['trigger']]}; anchor frame {anchor}, lead {e['lead_s']:.1f} s; "
        f"releasing team {team_names[e['team_id_i']]} (blue), won by {team_names[e['winning_team']]}.\n"
        f"Releasing team: p_static {e['p_static']:.2f}, p_dynamic {e['p_dynamic']:.2f}. {loser} lost: positioning "
        f"{e['deficit positioning']:.2f}, reading {e['deficit reading']:.2f}, after the anchor "
        f"{e['deficit after the anchor']:.2f}; verdict {e['verdict']}. Contours: each team's best reach time.",
        fontsize=9.5, color=INK, x=0.01, ha="left",
    )  # fmt: skip
    handles = [
        Line2D([], [], color=RELEASING, label="releasing team: contours and players (filled: detected)"),
        Line2D([], [], color=OTHER, label="other team: contours and players (filled: detected)"),
        Line2D([], [], marker="s", linestyle="", color=MUTED, label="goalkeeper"),
        Line2D([], [], marker="x", linestyle="", color=INK, markersize=9, label="pickup point"),
        Line2D([], [], marker="o", linestyle="", color=INK, markersize=6, label="ball at the anchor"),
        Line2D([], [], color=MUTED, linestyle=(0, (3, 3)), label="15 m radius; grey: camera view"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=8, frameon=False, labelcolor=MUTED)
    fig.tight_layout(rect=(0, 0.06, 1, 0.9))
    name = f"s5_episode_seed{SEED}_{k:02d}_{m}_{e['seq_i']}.png"
    fig.savefig(paths.FIGURES / name, dpi=130, facecolor=SURFACE)
    plt.close(fig)
    return name


def team_figure(ts: pd.DataFrame, team_names: dict) -> str:
    ts = ts.assign(name=ts["team"].map(team_names)).sort_values("deficit positioning")
    labels = [f"{n} ({lost} lost)" for n, lost in zip(ts["name"], ts["lost"])]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6), sharey=True, facecolor=SURFACE)
    for ax, share in zip(axes, decompose.SHARES):
        y = np.arange(len(ts))
        mid, lo, hi = ts[f"deficit {share}"], ts[f"deficit {share} lo"], ts[f"deficit {share} hi"]
        ax.set_facecolor(SURFACE)
        ax.hlines(y, lo, hi, color=RELEASING, linewidth=2, alpha=0.5)
        ax.scatter(mid, y, s=36, color=RELEASING, zorder=3)
        ax.axvline(0, color=MUTED, linewidth=0.8)
        ax.set_title(f"deficit share: {share}", fontsize=10, color=INK, loc="left")
        ax.grid(axis="x", color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        ax.tick_params(colors=MUTED, labelsize=8)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
    axes[0].set_yticks(np.arange(len(ts)), labels)
    fig.suptitle(
        "S5 team deficit shares over lost loose balls, exploration matches (bug check). Points: means; lines: 95% "
        "bootstrap intervals, episodes resampled within match.",
        fontsize=10, color=INK, x=0.01, ha="left",
    )  # fmt: skip
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    name = "s5_team_deficit_exploration.png"
    fig.savefig(paths.FIGURES / name, dpi=140, facecolor=SURFACE)
    plt.close(fig)
    return name


def main() -> None:
    ep = pd.read_csv(paths.AUDIT_DIR / "s5_episodes_exploration.csv")
    extra = pd.concat([episodes.all_episodes()]).set_index(["match_id", "seq_i"])
    cols = ["pickup_x", "pickup_y", "team_id_i", "player_id_next"]
    ep = ep.join(extra[cols], on=["match_id", "seq_i"])
    names = {}
    for m in paths.EXPLORATION:
        meta = io.load_metadata(m)
        names.update({meta[s]["id"]: meta[s]["short_name"] for s in ("home_team", "away_team")})
    pool = ep.sort_values(["match_id", "seq_i"]).reset_index(drop=True)
    drawn = pool.loc[np.random.default_rng(SEED).choice(len(pool), 4, replace=False)]
    print(f"seed {SEED}; pool: {len(pool)} analysis-set episodes\n")
    rows = []
    for k, (_, e) in enumerate(drawn.iterrows(), start=1):
        name = episode_figure(e, k, names)
        rows.append({"figure": k, "match_id": e["match_id"], "seq_i": e["seq_i"], "trigger": e["trigger"],
                     "verdict": e["verdict"], "file": f"audit/figures/{name}"})  # fmt: skip
    print(pd.DataFrame(rows).to_markdown(index=False))
    ts = pd.read_csv(paths.AUDIT_DIR / "s5_team_shares_exploration.csv")
    print(f"\nteam figure: audit/figures/{team_figure(ts, names)}")


if __name__ == "__main__":
    main()
