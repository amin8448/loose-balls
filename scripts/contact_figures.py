"""Contact figures, revision 3: the four episodes drawn with seed 20261028 under revision 2.

Under revision 2 they were drawn without replacement from the main pairs with 2 or more
contacts (AUDIT.md, contact figures). Revision 3 changes the pool, so the same four episodes
are redrawn for a before and after comparison; files carry the suffix _rev3.

Top row: the first-leg anchor frame, the last-leg anchor frame and the pickup frame, with the
contacts and the two anchors marked on the ball path. Bottom row: the three inputs of the
contact rule on each testable window frame (direction change, speed change, nearest player).
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from episode_figures import GRID, INK, MUTED, SURFACE, panel

from looseball import episodes, io, paths, tracking

SEED = 20261028
# (match_id, seq_i) of the revision 2 draw, in draw order
REV2_DRAW = [(1959846, 18), (1996436, 121), (1886347, 176), (1886347, 979)]
CONTACT = "#6250d6"


def overlay(ax, ep, fr):
    contacts = [int(f) for f in ep["contact_frames"].split(";") if f]
    ax.scatter(fr.loc[contacts, "ball_data.x"], fr.loc[contacts, "ball_data.y"], marker="D", s=60,
               facecolor="none", edgecolor=CONTACT, linewidth=1.6, zorder=7)  # fmt: skip
    for k, f in (("A1", ep["anchor1_frame"]), ("A2", ep["anchor2_frame"])):
        if pd.notna(f):
            x, y = fr.loc[int(f), ["ball_data.x", "ball_data.y"]]
            ax.scatter([x], [y], marker="^", s=70, color=INK, zorder=7)
            ax.annotate(
                k, (x, y), xytext=(-14, 6), textcoords="offset points", fontsize=8.5, color=INK, zorder=8
            )


def strips(axes, ep, fr, pl):
    rel, pk = int(ep["release_frame"]), int(ep["pickup_frame"])
    bx, by = fr["ball_data.x"].to_numpy(), fr["ball_data.y"].to_numpy()
    det = fr["ball_data.is_detected"].fillna(False).to_numpy(dtype=bool)
    t = episodes.contact_domain(rel, pk)
    t = t[det[t - 1] & det[t] & det[t + 1]]
    s_in, s_out, angle = episodes.ball_kinematics(bx, by, t)
    nearest = []
    for f in t:
        p = pl[pl["frame"] == f]
        nearest.append(np.hypot(p["x"] - bx[f], p["y"] - by[f]).min())
    contacts = [int(f) for f in ep["contact_frames"].split(";") if f]
    series = (
        (angle, episodes.CONTACT_ANGLE_DEG, "direction change (degrees)"),
        (np.abs(s_out - s_in), episodes.CONTACT_SPEED_CHANGE, "speed change (m/s)"),
        (np.array(nearest), episodes.CONTACT_PLAYER_RADIUS, "nearest player to ball (m)"),
    )
    for ax, (y, line, label) in zip(axes, series):
        ax.set_facecolor(SURFACE)
        ax.plot(t - rel, y, color=MUTED, linewidth=1, marker="o", markersize=2.5)
        ax.axhline(line, color=INK, linewidth=0.8, linestyle=(0, (3, 3)))
        for f in contacts:
            ax.axvline(f - rel, color=CONTACT, linewidth=1.2)
        for k, f in (("A1", ep["anchor1_frame"]), ("A2", ep["anchor2_frame"])):
            if pd.notna(f):
                ax.axvline(int(f) - rel, color=INK, linewidth=0.8, linestyle=":")
                ax.annotate(k, (int(f) - rel, 1), xycoords=("data", "axes fraction"), xytext=(2, -10),
                            textcoords="offset points", fontsize=8, color=INK)  # fmt: skip
        edge = episodes.CONTACT_EDGE
        ax.axvspan(0, edge - 0.5, color=GRID, alpha=0.7, linewidth=0)
        ax.axvspan(pk - rel - edge + 0.5, pk - rel, color=GRID, alpha=0.7, linewidth=0)
        ax.set_xlim(0, pk - rel)
        ax.set_title(label, fontsize=9, color=INK, loc="left")
        ax.set_xlabel("frames after release (pickup at the right edge)", fontsize=8, color=MUTED)
        ax.tick_params(colors=MUTED, labelsize=7.5)
        ax.grid(axis="y", color=GRID, linewidth=0.6)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)


def figure(ep, k, n):
    m = int(ep["match_id"])
    fr = tracking.load_frames(m).set_index("frame", drop=False)
    pl = tracking.load_players(m)
    meta = io.load_metadata(m)
    team_of = io.load_roster(m).set_index("id")["team_id"]
    fig = plt.figure(figsize=(18, 11), facecolor=SURFACE)
    gs = fig.add_gridspec(2, 3, height_ratios=[2.2, 1])
    top = [fig.add_subplot(gs[0, i]) for i in range(3)]
    bottom = [fig.add_subplot(gs[1, i]) for i in range(3)]
    a1 = ep["anchor1_frame"] if pd.notna(ep["anchor1_frame"]) else ep["leg1_start"]
    a2 = ep["anchor2_frame"] if pd.notna(ep["anchor2_frame"]) else ep["leg2_start"]
    for ax, label, f in (
        (top[0], "first-leg anchor (A1)", a1),
        (top[1], "last-leg anchor (A2)", a2),
        (top[2], "pickup", ep["pickup_frame"]),
    ):
        panel(ax, ep, fr, pl, team_of, label, int(f), meta)
        overlay(ax, ep, fr)
    strips(bottom, ep, fr, pl)
    lead = lambda v: f"{v:.1f} s" if pd.notna(v) else "no anchor"
    fig.suptitle(
        f"Contact figure {k} of {n}, revision 3 (episode drawn with seed {SEED} under revision 2). Match {m}, possessions {ep['seq_i']} to {ep['seq_next']}. "
        f"{episodes.TRIGGER_LABELS[ep['trigger']]}, resolution {ep['resolution']}, {ep['continuity']}.\n"
        f"Gap {ep['gap']} frames ({ep['gap'] / paths.FPS:.1f} s); {ep['n_contacts']} contacts at frames after release "
        f"{', '.join(str(int(f) - int(ep['release_frame'])) for f in ep['contact_frames'].split(';') if f) or 'none'}; "
        f"lead A1 {lead(ep['lead1_s'])}, A2 {lead(ep['lead2_s'])}. Purple: contacts; triangles and dotted lines: anchors; grey bands: edge frames not tested.",
        fontsize=10,
        color=INK,
        x=0.01,
        ha="left",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    name = f"contacts_seed{SEED}_{k:02d}_{m}_{ep['seq_i']}_rev3.png"
    fig.savefig(paths.FIGURES / name, dpi=110, facecolor=SURFACE)
    plt.close(fig)
    return name


def main():
    ep = episodes.all_episodes()
    drawn = pd.concat([ep[(ep["match_id"] == m) & (ep["seq_i"] == q)] for m, q in REV2_DRAW])
    assert len(drawn) == len(REV2_DRAW) and drawn["main"].all()
    print(f"revision 3 redraw of the revision 2 draw (seed {SEED})\n")
    rows = []
    for k, (_, e) in enumerate(drawn.iterrows(), start=1):
        name = figure(e, k, len(drawn))
        rows.append({"figure": k, "match_id": e["match_id"], "seq_i": e["seq_i"], "trigger": e["trigger"],
                     "contacts": e["n_contacts"], "gap": e["gap"], "file": f"audit/figures/{name}"})  # fmt: skip
    print(pd.DataFrame(rows).to_markdown(index=False))


if __name__ == "__main__":
    main()
