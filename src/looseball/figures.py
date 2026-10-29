"""The README figures, part of `looseball reproduce` (step 3b).

Figure 1, the worked episode: one lost ball from match 1927964, drawn by seed among those with a
reading or positioning verdict, on its anchor frame. Figure 2, the test-set result, versions A
(team verdict shares and the per-match log-loss of the four models) and B (team verdict shares
alone). Every number comes from the reproduce output tables or is computed by the package.
"""

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle

from looseball import find_episodes
from looseball.adapters.skillcorner import load_match
from looseball.decompose import SHARES
from looseball.expectation import log_loss
from looseball.race import RADIUS, ReachModel
from looseball.velocities import tracking_velocities

WORKED_MATCH = 1927964
SEED = 20261029
SURFACE, INK, MUTED, GRID, NEUTRAL = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#f2f1ee"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
VERDICT_COLOURS = {"positioning": BLUE, "reading": ORANGE, "after the anchor": AQUA}
HALF = 22.0  # metres shown around the pickup point
MAX_CAPTION_WORDS = 40
MIN_LEAD = 1.5  # seconds, Figure 1 legibility constraint (AUDIT.md, 3b revision)
MIN_PATH = 10.0  # metres
STYLE = {
    "font.size": 12,
    "axes.edgecolor": GRID,
    "axes.labelcolor": MUTED,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
}


def _pitch(ax, length: float, width: float) -> None:
    hl, hw = length / 2, width / 2
    kw = {"color": "#bebdb7", "linewidth": 1.1, "zorder": 1}
    ax.add_patch(Rectangle((-hl, -hw), length, width, fill=False, **kw))
    ax.plot([0, 0], [-hw, hw], **kw)
    ax.add_patch(Circle((0, 0), 9.15, fill=False, **kw))
    for s in (-1, 1):
        ax.add_patch(Rectangle((s * hl - (16.5 if s > 0 else 0), -20.16), 16.5, 40.32, fill=False, **kw))
        ax.add_patch(Rectangle((s * hl - (5.5 if s > 0 else 0), -9.16), 5.5, 18.32, fill=False, **kw))


def ball_path_length(tracking: pd.DataFrame, release: int, pickup: int) -> float:
    """Length of the tracked ball path from release to pickup, steps with a missing position skipped."""
    xy = tracking.loc[release:pickup, ["ball_x", "ball_y"]].to_numpy(dtype=float)
    return float(np.nansum(np.hypot(np.diff(xy[:, 0]), np.diff(xy[:, 1]))))


def draw_episode(episodes: pd.DataFrame, path_length: pd.Series | None = None) -> pd.Series:
    """The seeded draw for Figure 1 from the reproduce output's episodes table, under the
    legibility constraint logged before the draw (AUDIT.md, 3b revision): a reading or
    positioning verdict, a lead of at least MIN_LEAD and a ball path of at least MIN_PATH.
    path_length: ball path length by seq_i for the worked match."""
    pool = episodes[
        (episodes["match_id"] == WORKED_MATCH) & episodes["verdict"].isin(["reading", "positioning"])
    ]
    pool = pool[pool["lead_s"] >= MIN_LEAD]
    if path_length is not None:
        pool = pool[pool["seq_i"].map(path_length) >= MIN_PATH]
    pool = pool.sort_values("seq_i").reset_index(drop=True)
    return pool.loc[int(np.random.default_rng(SEED).choice(len(pool)))], len(pool)


def caption(loser: str, p_static_loser: float, p_dynamic_loser: float, verdict: str) -> str:
    text = (
        f"Shading: which team reaches each point first. When the drop zone came into view, {loser} had "
        f"{100 * p_static_loser:.1f}% from position, {100 * p_dynamic_loser:.1f}% with movement: lost on {verdict}. "
        f"Randomly drawn among lost balls with lead {MIN_LEAD:g} s+ and path {MIN_PATH:g} m+."
    )
    if len(text.split()) > MAX_CAPTION_WORDS:
        raise ValueError(f"caption has {len(text.split())} words")
    return text


def figure1(data, episodes: pd.DataFrame, out_dir: Path) -> dict:
    m = load_match(data, WORKED_MATCH)
    found = find_episodes(m.possessions, m.tracking, m.players).set_index("seq_i")
    lengths = pd.Series(
        {
            s: ball_path_length(m.tracking, int(r.release_frame), int(r.pickup_frame))
            for s, r in found.iterrows()
        }
    )
    e, pool_size = draw_episode(episodes, lengths)
    ep = found.loc[int(e["seq_i"])]
    anchor, release, pickup = int(e["anchor_frame"]), int(ep["release_frame"]), int(e["pickup_frame"])
    target = np.array([ep["pickup_x"], ep["pickup_y"]], dtype=float)
    loser, winner = int(e["losing_team"]), int(e["winning_team"])
    won = int(e["releasing_won"]) == 1
    ps_loser = 1 - e["p_static"] if won else e["p_static"]
    pd_loser = 1 - e["p_dynamic"] if won else e["p_dynamic"]
    length, width = m.pitch_dimensions
    xlim = (max(target[0] - HALF, -length / 2 - 2), min(target[0] + HALF, length / 2 + 2))
    ylim = (max(target[1] - HALF, -width / 2 - 2), min(target[1] + HALF, width / 2 + 2))

    vel = tracking_velocities(m.tracking)
    at = vel[vel["frame"] == anchor].copy()
    inside = at["x"].between(*xlim) & at["y"].between(*ylim)
    at["team_id"] = m.players.set_index("column_id")["team_id"].reindex(at["column_id"]).to_numpy()
    model = ReachModel()
    gx, gy = np.meshgrid(np.linspace(*xlim, 177), np.linspace(*ylim, 177))
    grid = np.column_stack([gx.ravel(), gy.ravel()])

    def best(team: int) -> np.ndarray:
        rows = at[at["team_id"] == team]
        times = [
            model.tti(np.array([p.x, p.y]), grid, np.nan_to_num(np.array([p.vx, p.vy])))
            for p in rows.itertuples()
        ]
        return np.min(times, axis=0).reshape(gx.shape)

    margin = np.clip(best(loser) - best(winner), -2.0, 2.0)  # positive: the winning team gets there first
    cmap = LinearSegmentedColormap.from_list("margin", [ORANGE, NEUTRAL, BLUE])

    with plt.rc_context(STYLE):
        fig = plt.figure(figsize=(10, 10.4), facecolor=SURFACE)
        ax = fig.add_axes([0.03, 0.40, 0.94, 0.50])
        cax = fig.add_axes([0.16, 0.335, 0.68, 0.018])
        ax.set_facecolor(SURFACE)
        cf = ax.contourf(gx, gy, margin, levels=np.arange(-2.0, 2.01, 0.25), cmap=cmap, alpha=0.6, zorder=0)
        ax.contour(gx, gy, margin, levels=[0.0], colors=INK, linewidths=1.0, zorder=2)
        _pitch(ax, length, width)
        ax.add_patch(
            Circle(
                tuple(target), RADIUS, fill=False, color=MUTED, linewidth=1.0, linestyle=(0, (4, 3)), zorder=2
            )
        )
        path = m.tracking.loc[release:pickup, ["ball_x", "ball_y"]].to_numpy(dtype=float)
        ax.plot(path[:, 0], path[:, 1], color=INK, linewidth=1.6, zorder=4)
        ax.scatter(path[0, 0], path[0, 1], s=50, facecolor=SURFACE, edgecolor=INK, linewidth=1.5, zorder=5)
        ax.scatter(*target, marker="x", s=150, color=INK, linewidth=2.4, zorder=6)
        for team, colour in ((winner, BLUE), (loser, ORANGE)):
            rows = at[(at["team_id"] == team) & inside]  # players inside the panel
            det = rows["detected"].fillna(False).to_numpy(dtype=bool)
            ax.scatter(rows["x"], rows["y"], s=120, facecolor=np.where(det, colour, SURFACE), edgecolor=colour,
                       linewidth=2.2, zorder=7)  # fmt: skip
            for p in rows.itertuples():
                if not np.isnan(p.vx):
                    ax.annotate("", (p.x + p.vx, p.y + p.vy), (p.x, p.y), zorder=8,
                                arrowprops={"arrowstyle": "-|>", "color": colour, "lw": 1.8, "mutation_scale": 13})  # fmt: skip
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal")
        ax.set_xticks([])
        ax.set_yticks([])
        cb = fig.colorbar(cf, cax=cax, orientation="horizontal", ticks=[-2, -1, 0, 1, 2])
        cb.ax.set_xticklabels([f"{m.team_names[loser]}\nfirst by 2 s", "1 s", "level", "1 s",
                               f"{m.team_names[winner]}\nfirst by 2 s"])  # fmt: skip
        cb.ax.tick_params(labelsize=10.5, colors=MUTED)
        cb.outline.set_edgecolor(GRID)
        cb.ax.set_title(
            "shading: which team gets to each point first, and by how much", fontsize=11, color=MUTED
        )
        clock = m.tracking.loc[anchor, "clock"]
        fig.text(0.03, 0.965, f"{m.team_names[m.home_team_id]} v {m.team_names[m.away_team_id]}, match clock {clock}",
                 fontsize=14, color=INK)  # fmt: skip
        fig.text(
            0.03, 0.932, "The anchor frame: the moment the drop zone came into view", fontsize=12, color=MUTED
        )
        handles = [
            Line2D([], [], marker="o", linestyle="", markersize=10, color=BLUE, label=f"{m.team_names[winner]} (won the ball)"),
            Line2D([], [], marker="o", linestyle="", markersize=10, color=ORANGE, label=f"{m.team_names[loser]} (lost it)"),
            Line2D([], [], marker="o", linestyle="", markersize=10, markerfacecolor=SURFACE, markeredgecolor=MUTED,
                   label="hollow: position estimated, off camera"),
            Line2D([], [], color=MUTED, lw=1.8, label="arrow: one second of current movement"),
            Line2D([], [], color=INK, lw=1.6, marker="o", markerfacecolor=SURFACE, label="ball path, release to pickup"),
            Line2D([], [], marker="x", linestyle="", markersize=11, color=INK, label="pickup point"),
            Line2D([], [], color=MUTED, linestyle=(0, (4, 3)), label="15 m race radius"),
            Line2D([], [], color=INK, lw=1.0, label="level line: both teams equally fast"),
        ]  # fmt: skip
        fig.legend(
            handles=handles,
            loc="upper left",
            bbox_to_anchor=(0.03, 0.27),
            ncol=2,
            fontsize=10.5,
            frameon=False,
        )
        text = caption(m.team_names[loser], ps_loser, pd_loser, e["verdict"])
        fig.text(0.03, 0.155, textwrap.fill(text, 98), fontsize=12, color=INK, va="top")
        name = f"figure1_constrained_seed{SEED}.png"
        fig.savefig(out_dir / name, dpi=150, facecolor=SURFACE, bbox_inches="tight", pad_inches=0.3)
        plt.close(fig)
    (out_dir / "figure1_caption.txt").write_text(text + "\n")
    return {"file": name, "seed": SEED, "match_id": WORKED_MATCH, "seq_i": int(e["seq_i"]), "verdict": e["verdict"],
            "pool": pool_size, "lead_s": float(e["lead_s"]), "ball_path_m": float(lengths[int(e["seq_i"])]),
            "caption": text}  # fmt: skip


def _team_panel(ax, teams: pd.DataFrame) -> None:
    t = teams.sort_values("positioning").reset_index(drop=True)
    y = np.arange(len(t))
    left = np.zeros(len(t))
    for v in SHARES:
        ax.barh(
            y, t[v], left=left, height=0.66, color=VERDICT_COLOURS[v], edgecolor=SURFACE, linewidth=2, label=v
        )
        for yi, (lft, w) in enumerate(zip(left, t[v])):
            if w >= 0.07:
                ax.text(
                    lft + w / 2,
                    yi,
                    f"{100 * w:.0f}%",
                    ha="center",
                    va="center",
                    fontsize=10.5,
                    color=INK if v == "after the anchor" else "white",
                    fontweight="bold",
                )
        left = left + t[v].to_numpy()
    lo, hi = t["positioning lo"].to_numpy(), t["positioning hi"].to_numpy()
    ax.hlines(y - 0.42, lo, hi, color=INK, linewidth=1.6, zorder=5)  # below the bar
    ax.vlines(np.r_[lo, hi], np.r_[y, y] - 0.47, np.r_[y, y] - 0.37, color=INK, linewidth=1.6, zorder=5)
    labels = [f"{n}{' *' if f == 'flag' else ''} ({lost})" for n, f, lost in
              zip(t["team"], t["sample-size flag"].fillna(""), t["lost"])]  # fmt: skip
    ax.set_yticks(y, labels, fontsize=12, color=INK)
    ax.set_ylim(-0.6, len(t) - 0.4)
    ax.set_xlim(0, 1)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("share of the team's lost loose balls (number lost)")
    ax.legend(
        loc="lower left", bbox_to_anchor=(0.0, 1.0), ncol=3, frameon=False, fontsize=12, handlelength=1.2
    )
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.text(0, -0.13, "Line under each bar: 95% interval on the positioning share.\n* Two test matches or fewer.",
            fontsize=10.5, color=MUTED, transform=ax.transAxes, va="top")  # fmt: skip


def _model_panel(ax, episodes: pd.DataFrame) -> int:
    models = [("p_B0", "B0\nplayer\ncount"), ("p_B1", "B1\nnearest\nplayer"), ("p_static", "static\npositions"),
              ("p_dynamic", "dynamic\npositions,\nmovement")]  # fmt: skip
    per = pd.DataFrame(
        {
            col: {m: log_loss(g["releasing_won"], g[col]) for m, g in episodes.groupby("match_id")}
            for col, _ in models
        }
    )
    x = np.arange(len(models))
    for _, row in per.iterrows():
        ax.plot(x, row.to_numpy(), color="#b9b8b2", linewidth=1.1, zorder=1)
        ax.scatter(x[:-1], row.to_numpy()[:-1], s=22, color=MUTED, zorder=2)
    ax.scatter([x[-1]] * len(per), per["p_dynamic"], s=30, color=BLUE, zorder=3)
    lowest = int((per["p_dynamic"] < per.drop(columns="p_dynamic").min(axis=1)).sum())
    ax.set_xticks(x, [label for _, label in models], fontsize=11)
    ax.set_xlim(-0.35, len(models) - 0.65)
    ax.set_ylabel("log-loss per test match (lower is better)")
    ax.set_title(f"Dynamic lowest in {lowest} of {len(per)} matches", fontsize=12.5, color=INK, loc="left")
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return lowest


def figure2(teams: pd.DataFrame, episodes: pd.DataFrame, out_dir: Path) -> dict:
    files = {}
    with plt.rc_context(STYLE):
        fig, (left, right) = plt.subplots(1, 2, figsize=(13, 7.2), facecolor=SURFACE,
                                          gridspec_kw={"width_ratios": [1.55, 1]})  # fmt: skip
        for ax in (left, right):
            ax.set_facecolor(SURFACE)
        _team_panel(left, teams)
        lowest = _model_panel(right, episodes)
        fig.text(0.01, 0.955, "Why lost loose balls were lost, and whether the race predicts who wins: 15 held-out matches",
                 fontsize=14, color=INK)  # fmt: skip
        fig.subplots_adjust(left=0.205, right=0.985, top=0.835, bottom=0.2, wspace=0.22)
        files["A"] = "figure2_A.png"
        fig.savefig(out_dir / files["A"], dpi=150, facecolor=SURFACE)
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(9, 7.2), facecolor=SURFACE)
        ax.set_facecolor(SURFACE)
        _team_panel(ax, teams)
        fig.text(
            0.01,
            0.955,
            "Why lost loose balls were lost, by team: 15 held-out matches",
            fontsize=14,
            color=INK,
        )
        fig.subplots_adjust(left=0.3, right=0.97, top=0.835, bottom=0.2)
        files["B"] = "figure2_B.png"
        fig.savefig(out_dir / files["B"], dpi=150, facecolor=SURFACE)
        plt.close(fig)
    return {"files": files, "dynamic lowest in matches": lowest}


def draw_figures(data, out) -> dict:
    """Figures 1 and 2 (A and B) into OUT/figures, from the reproduce output tables in OUT."""
    out = Path(out)
    fig_dir = out / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    episodes = pd.read_csv(out / "episodes.csv")
    teams = pd.read_csv(out / "team_verdicts.csv")
    return {"figure 1": figure1(data, episodes, fig_dir), "figure 2": figure2(teams, episodes, fig_dir)}
