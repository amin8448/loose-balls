"""Step 3h: what would have been enough, its checks C1 to C7 and the path check P1 to P3
(report-only; AUDIT.md "3h. What would have been enough" and "Path check: procedure").

Usage: python scripts/s3h.py exploration
Runs on the five exploration matches as a rehearsal (bug check), with four seeded episode figures
(seed 20261117: two redirect, two move) showing the enough change on the anchor frame. Outputs
to audit/s3h_exploration/ and audit/figures/. The test-set run is the next step and is not
started by this script.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle
from scipy.stats import spearmanr

from looseball.adapters.skillcorner import load_match
from looseball.enough import TIE, TYPES, _rotate, rotation_closed_form
from looseball.export_clips import export_clips_enough
from looseball.pathcheck import TOLERANCES, path_check
from looseball.race import RADIUS, REACTION, TOP_SPEED, ReachModel
from looseball.report import bootstrap_within_match
from looseball.reproduce import N_BOOT, SEED, VARIANTS, compute, enough_tables
from looseball.velocities import tracking_velocities

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "opendata"
SETS = {"exploration": (1886347, 1959846, 1996435, 1996436, 2007448)}
FIGURE_SEED = 20261117
HALF = 22.0
BLUE, ORANGE, INK, MUTED = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e"
LOST = ("positioning", "reading")


def md(t: pd.DataFrame, floatfmt: str = ".3f") -> str:
    return t.to_markdown(index=False, floatfmt=floatfmt)


def q(x) -> dict:
    x = pd.Series(x, dtype=float).dropna()
    if x.empty:
        return {"n": 0, "p10": np.nan, "p50": np.nan, "p90": np.nan}
    return {"n": len(x), "p10": x.quantile(0.1), "p50": x.quantile(0.5), "p90": x.quantile(0.9)}


def new_time(row, race: pd.DataFrame, target, model: ReachModel) -> float:
    """Bug check: the enough player's reach time after the enough change (frozen model)."""
    p = race[race["column_id"] == row.enough_player].iloc[0]
    pos, vel = np.array([p.x, p.y], float), np.nan_to_num(np.array([p.vx, p.vy], float))
    if row.enough_type == "move":
        drift = target - (pos + REACTION * vel)
        return model.tti(pos + row.enough_metres * drift / np.hypot(*drift), target, vel)
    u = target - pos
    side = 1.0 if (vel[0] * u[1] - vel[1] * u[0]) >= 0 else -1.0
    return model.tti(pos, target, _rotate(vel, side * np.radians(row.enough_degrees)))


def checks(r: dict, tabs: dict) -> tuple[str, pd.DataFrame]:
    a = r["a"]
    key = ["match_id", "seq_i"]
    e = a[
        [
            *key,
            "trigger",
            "verdict",
            "loser_side",
            "pickup_x",
            "pickup_y",
            "p_static_loser",
            "p_dynamic_loser",
        ]
    ]
    e = e.merge(tabs["a"], on=key, validate="1:1")
    e["type"] = e["enough_type"].fillna("blank (after the anchor)")
    out = [f"3h rehearsal on {r['n_sets']} matches: {len(e)} lost balls in the analysis set.\n"]

    out.append("C1. Counts by enough_type, by verdict and by trigger:\n")
    order = [*TYPES, "blank (after the anchor)"]
    c1 = pd.crosstab(e["verdict"], e["type"], margins=True, margins_name="all").reindex(
        columns=[*order, "all"], fill_value=0
    )
    out.append(md(c1.reset_index(), ".0f") + "\n")
    c1t = pd.crosstab(e["trigger"], e["type"], margins=True, margins_name="all").reindex(
        columns=[*order, "all"], fill_value=0
    )
    out.append(md(c1t.reset_index(), ".0f") + "\n")

    out.append(
        "C2 and C3. metres_short (balls with D > 0) and enough_degrees (redirect balls), by verdict:\n"
    )
    rows = []
    for v in LOST:
        d = e[e["verdict"] == v]
        rows.append({"quantity": "metres_short, m", "verdict": v, **q(d["metres_short"])})
        rows.append(
            {
                "quantity": "enough_degrees",
                "verdict": v,
                **q(d.loc[d["enough_type"] == "redirect", "enough_degrees"]),
            }
        )
        rows.append(
            {
                "quantity": "enough_metres (move), m",
                "verdict": v,
                **q(d.loc[d["enough_type"] == "move", "enough_metres"]),
            }
        )
    c23 = pd.DataFrame(rows)
    out.append(md(c23, ".2f") + "\n")
    med = {
        v: c23.loc[(c23["quantity"] == "metres_short, m") & (c23["verdict"] == v), "p50"].iloc[0]
        for v in LOST
    }
    flags = [v for v in LOST if med[v] > 10]
    out.append(
        f"Reading rule (median metres_short above 10 m): positioning {med['positioning']:.2f} m, reading "
        f"{med['reading']:.2f} m; {'above 10 m for ' + ', '.join(flags) if flags else 'neither is above 10 m'}.\n"
    )

    reading = e[e["verdict"] == "reading"]
    out.append(
        f"C4. Reading verdicts fixed by one redirection: {(reading['enough_type'] == 'redirect').sum()} of "
        f"{len(reading)} ({(reading['enough_type'] == 'redirect').mean():.3f}).\n"
    )
    who = e[e["enough_type"].isin(["redirect", "move"])]
    out.append(
        f"C5. Of {len(who)} balls with an enough player: extrapolated at the anchor "
        f"{who['enough_player_extrapolated'].sum()} ({who['enough_player_extrapolated'].mean():.3f}); goalkeeper "
        f"{who['enough_player_gk'].sum()} ({who['enough_player_gk'].mean():.3f}).\n"
    )

    out.append(
        "C6. Stability under each V3 variant (positioning and reading balls whose verdict is unchanged):\n"
    )
    rows = []
    base = e[e["verdict"].isin(LOST)].set_index(key)
    for name in VARIANTS:
        v = tabs[name].set_index(key).reindex(base.index)
        vverdict = pd.Series(r["variant_verdicts"][name], index=pd.MultiIndex.from_frame(a[key])).reindex(
            base.index
        )
        same_v = vverdict == base["verdict"]
        b, w = base[same_v], v[same_v]
        same = (b["enough_type"] == w["enough_type"]) & (
            b["enough_player"].fillna("") == w["enough_player"].fillna("")
        )
        row = {"variant": name, "balls": len(base), "left out (verdict changed)": 1 - same_v.mean(), "kept": len(b),
               "type and player unchanged": same.mean()}  # fmt: skip
        for t, col in (("redirect", "enough_degrees"), ("move", "enough_metres")):
            both = (b["enough_type"] == t) & (w["enough_type"] == t)
            n = int(both.sum())
            row[f"{t}: n both"] = n
            row[f"{t}: Spearman"] = (
                spearmanr(b.loc[both, col], w.loc[both, col]).statistic if n >= 3 else np.nan
            )
        rows.append(row)
    out.append(md(pd.DataFrame(rows)) + "\n")

    off = r["off"][[*key, "verdict"]].merge(tabs["off"], on=key, validate="1:1")
    rows = []
    for v in LOST:
        d = off[off["verdict"] == v]
        rows.append({"verdict": v, "ungated lost balls": len(d), "median metres_short": d["metres_short"].median(),
                     "median enough_degrees": d.loc[d["enough_type"] == "redirect", "enough_degrees"].median()})  # fmt: skip
    out.append("C7. Ungated lost balls (D7 off), report-only line:\n")
    out.append(md(pd.DataFrame(rows), ".2f") + "\n")

    model = ReachModel()
    races = dict(tuple(r["reach"].groupby(key, sort=False)))
    errs = []
    for row in e[e["enough_type"].isin(["redirect", "move"])].itertuples(index=False):
        race = races[(row.match_id, row.seq_i)]
        t_w = race.loc[race["side"] != row.loser_side, "t_dynamic"].min()
        errs.append(abs(new_time(row, race, np.array([row.pickup_x, row.pickup_y]), model) - t_w))
    prec, tie_best, tie_rot = 0, 0, 0
    for row in e[e["verdict"].isin(LOST)].itertuples(index=False):
        race = races[(row.match_id, row.seq_i)]
        losing = race[race["side"] == row.loser_side]
        players = losing[~losing["empty_team"].astype(bool)]
        prec += int(row.deficit_s <= 0 and players.empty)
        if row.deficit_s > 0 and not players.empty:
            tie_best += int((players["t_dynamic"] <= players["t_dynamic"].min() + TIE).sum() > 1)
            t_w = race.loc[race["side"] != row.loser_side, "t_dynamic"].min()
            rots = []
            for p in players.itertuples(index=False):
                v = np.array([p.vx, p.vy], float)
                sp = float(np.hypot(*v)) if np.isfinite(v).all() else 0.0
                if sp > 0 and p.dist > 0:
                    to = np.array([row.pickup_x - p.x, row.pickup_y - p.y])
                    phi = float(np.arccos(np.clip(v @ to / (sp * p.dist), -1, 1)))
                    rots.append(
                        rotation_closed_form(p.dist, REACTION * sp, TOP_SPEED * (t_w - REACTION), phi)
                    )
            rots = np.array([x for x in rots if np.isfinite(x)])
            tie_rot += int(len(rots) > 1 and (rots <= rots.min() + TIE).sum() > 1)
    out.append(
        f"Diagnostics: precedence rule (a) (D <= 0 with an empty losing side, typed already_favourite) applied to "
        f"{prec} balls; the best-placed tie rule decided {tie_best} balls and the rotation tie rule {tie_rot}.\n"
    )
    out.append(
        f"Bug check: after the enough change the player's reach time equals t_w for all {len(errs)} redirect and "
        f"move balls (largest difference {max(errs):.2e} s).\n"
    )
    return "\n".join(out), e


def path_report(e: pd.DataFrame, paths: pd.DataFrame) -> str:
    p = e.merge(paths, on=["match_id", "seq_i"], validate="1:1")
    g = p[p["ground"]].reset_index(drop=True)
    head = (
        f"Path check on {len(p)} lost balls: {len(g)} ground, {len(p) - len(g)} aerial (left out). "
        f"Ball-detected path frames per ground ball: median {g['path_frames'].median():.0f}.\n"
    )
    out = [head]
    frozen = np.where(
        g["p_dynamic_loser"] > 0.5, "loser", np.where(g["p_dynamic_loser"] < 0.5, "winner", "none")
    )
    for tol in TOLERANCES:
        k = f"{tol:g}"
        dyn = g[f"dynamic {k} favourite"]
        cat = np.select([frozen == "none", dyn == "unreached", dyn == "tie", dyn == frozen],
                        ["frozen: no favourite", "path: unreached", "path: tie", "agree"], "disagree")  # fmt: skip
        counts = (
            pd.Series(cat)
            .value_counts()
            .reindex(
                ["agree", "disagree", "path: tie", "path: unreached", "frozen: no favourite"], fill_value=0
            )
        )
        out.append(f"P1, tolerance {k} s. Dynamic path favourite against the frozen dynamic favourite "
                   f"(share agree {counts['agree'] / len(g):.3f} of {len(g)}):\n")  # fmt: skip
        out.append(
            md(counts.rename("balls").reset_index().rename(columns={"index": "category"}), ".0f") + "\n"
        )
        st = g[f"static {k} favourite"].map({"loser": "loser is path favourite", "winner": "winner is",
                                              "tie": "tie", "unreached": "unreached"})  # fmt: skip
        tab = pd.crosstab(g["verdict"], st, margins=True, margins_name="all")
        out.append(f"P2, tolerance {k} s. Frozen verdict by the loser's static path status:\n")
        out.append(md(tab.reset_index(), ".0f") + "\n")
        pos = g[g["verdict"] == "positioning"].reset_index(drop=True)

        def share(d, k=k):
            return (d[f"static {k} favourite"] == "loser").mean()

        boot = np.array(bootstrap_within_match(pos, share, N_BOOT, SEED))
        out.append(
            f"P3, tolerance {k} s. Positioning verdicts where the loser is the static path favourite: "
            f"{int((pos[f'static {k} favourite'] == 'loser').sum())} of {len(pos)}, {share(pos):.3f} "
            f"(95% interval {np.quantile(boot, 0.025):.3f} to {np.quantile(boot, 0.975):.3f}).\n"
        )
    return "\n".join(out)


def draw(ball, match, vel: pd.DataFrame, race: pd.DataFrame, episode, path: Path) -> None:
    """One rehearsal figure: the anchor frame with the enough change drawn."""
    anchor, release, pickup = int(episode.anchor_frame), int(episode.release_frame), int(episode.pickup_frame)
    target = np.array([episode.pickup_x, episode.pickup_y], float)
    at = vel[vel["frame"] == anchor].copy()
    at["team_id"] = match.players.set_index("column_id")["team_id"].reindex(at["column_id"]).to_numpy()
    loser, winner = int(episode.losing_team), int(episode.winning_team)
    t_w = race.loc[race["side"] != ball.loser_side, "t_dynamic"].min()
    big_r = TOP_SPEED * (t_w - REACTION)
    fig, ax = plt.subplots(figsize=(8, 8.6))
    ax.add_patch(Circle(tuple(target), RADIUS, fill=False, color=MUTED, ls=(0, (4, 3)), lw=1))
    ax.add_patch(Circle(tuple(target), big_r, fill=False, color=INK, ls=":", lw=1.2))
    trk = match.tracking.loc[release:pickup, ["ball_x", "ball_y"]].to_numpy(dtype=float)
    ax.plot(trk[:, 0], trk[:, 1], color=INK, lw=1.4)
    ax.scatter(*target, marker="x", s=120, color=INK, lw=2.2, zorder=6)
    for team, colour in ((winner, BLUE), (loser, ORANGE)):
        rows = at[
            (at["team_id"] == team)
            & ((at["x"] - target[0]).abs() <= HALF)
            & ((at["y"] - target[1]).abs() <= HALF)
        ]
        det = rows["detected"].fillna(False).to_numpy(dtype=bool)
        ax.scatter(
            rows["x"],
            rows["y"],
            s=90,
            facecolor=np.where(det, colour, "white"),
            edgecolor=colour,
            lw=2,
            zorder=7,
        )
        for p in rows.itertuples():
            if np.isfinite(p.vx):
                ax.annotate(
                    "",
                    (p.x + p.vx, p.y + p.vy),
                    (p.x, p.y),
                    arrowprops={"arrowstyle": "-|>", "color": colour, "lw": 1.5},
                )
    p = race[race["column_id"] == ball.enough_player].iloc[0]
    pos, v = np.array([p.x, p.y], float), np.nan_to_num(np.array([p.vx, p.vy], float))
    ax.scatter(*pos, s=320, facecolor="none", edgecolor=INK, lw=1.5, zorder=8)
    drift = pos + REACTION * v
    ax.scatter(*drift, s=30, color=ORANGE, marker="s", zorder=8)
    if ball.enough_type == "redirect":
        u = target - pos
        side = 1.0 if (v[0] * u[1] - v[1] * u[0]) >= 0 else -1.0
        nv = _rotate(v, side * np.radians(ball.enough_degrees))
        ax.annotate(
            "",
            tuple(pos + nv),
            tuple(pos),
            arrowprops={"arrowstyle": "-|>", "color": INK, "lw": 1.8, "ls": "--"},
        )
        ax.scatter(*(pos + REACTION * nv), s=40, color=INK, marker="s", zorder=8)
        what = f"redirect {p.column_id} by {ball.enough_degrees:.1f} degrees"
    else:
        w = (target - drift) / np.hypot(*(target - drift))
        moved = pos + ball.enough_metres * w
        ax.plot(*np.c_[pos, moved], color=INK, ls="--", lw=1.4)
        ax.scatter(*moved, s=90, facecolor="none", edgecolor=INK, lw=1.5, linestyles="--", zorder=8)
        ax.scatter(*(moved + REACTION * v), s=40, color=INK, marker="s", zorder=8)
        what = f"move {p.column_id} {ball.enough_metres:.1f} m closer"
    ax.set_xlim(target[0] - HALF, target[0] + HALF)
    ax.set_ylim(target[1] - HALF, target[1] + HALF)
    ax.set_aspect("equal")
    ax.set_title(
        f"{match.team_names[match.home_team_id]} v {match.team_names[match.away_team_id]}, match {episode.match_id}, "
        f"seq_i {episode.seq_i}, {episode.trigger}, anchor frame {anchor}\n"
        f"lost by {match.team_names[loser]} (orange): verdict {ball.verdict}; p_static {ball.p_static_loser:.3f}, "
        f"p_dynamic {ball.p_dynamic_loser:.3f}; D {ball.deficit_s:.2f} s\nenough: {what}",
        fontsize=10, loc="left",
    )  # fmt: skip
    fig.text(0.02, 0.015, "Squares: positions after the 0.7 s reaction drift (orange: as recorded; black: after the change). "
             "Dotted circle: radius 5 x (t_w - 0.7) around the pickup point; a black square on it means the change "
             "exactly reaches t_w. Hollow: extrapolated. Dashed circle: 15 m race.", fontsize=7.5, wrap=True)  # fmt: skip
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def main(name: str) -> None:
    if name not in SETS:
        raise SystemExit(f"set must be one of {sorted(SETS)}")
    matches = SETS[name]
    out = ROOT / "audit" / f"s3h_{name}"
    out.mkdir(parents=True, exist_ok=True)
    r = compute(DATA, matches=matches)
    tabs = enough_tables(r)
    text, e = checks(r, tabs)
    a = r["a"]
    export_clips_enough(a[["match_id", "seq_i", "losing_team", "verdict"]], a[["match_id", "seq_i", "period_id", "anchor_frame"]],
                        r["clocks"], tabs["a"], path=out / "clips_enough.csv")  # fmt: skip
    pd.concat([t.assign(set=k) for k, t in tabs.items()]).to_csv(
        out / "enough_all_sets.csv", index=False, float_format="%.4f"
    )

    pool = (
        e[e["enough_type"].isin(["redirect", "move"])]
        .sort_values(["match_id", "seq_i"])
        .reset_index(drop=True)
    )
    rng = np.random.default_rng(FIGURE_SEED)
    drawn = []
    for t in ("redirect", "move"):
        sub = pool[pool["enough_type"] == t].reset_index(drop=True)
        drawn += [sub.loc[i] for i in rng.choice(len(sub), 2, replace=False)]
    episodes = a.set_index(["match_id", "seq_i"])
    races = dict(tuple(r["reach"].groupby(["match_id", "seq_i"], sort=False)))

    paths, figures = [], []
    for mid in matches:
        m = load_match(DATA, mid)
        vel = tracking_velocities(m.tracking)
        balls = a.loc[a["match_id"] == mid, ["match_id", "seq_i", "release_frame", "anchor_frame", "pickup_frame",
                                             "losing_team", "winning_team"]]  # fmt: skip
        paths.append(path_check(balls, m.tracking, vel, m.players))
        for k, ball in enumerate(drawn, start=1):
            if ball.match_id != mid:
                continue
            ep = episodes.loc[(ball.match_id, ball.seq_i)]
            ep = ep.to_frame().T.assign(match_id=ball.match_id, seq_i=ball.seq_i).iloc[0]
            f = (
                ROOT
                / "audit"
                / "figures"
                / f"s3h_{name}_seed{FIGURE_SEED}_{k:02d}_{ball.enough_type}_{mid}_{ball.seq_i}.png"
            )
            draw(ball, m, vel, races[(ball.match_id, ball.seq_i)], ep, f)
            figures.append({"figure": k, "match_id": mid, "seq_i": ball.seq_i, "trigger": ball.trigger,
                            "verdict": ball.verdict, "enough_type": ball.enough_type, "enough_player": ball.enough_player,
                            "magnitude": ball.enough_degrees if ball.enough_type == "redirect" else ball.enough_metres,
                            "file": str(f.relative_to(ROOT))})  # fmt: skip
    paths = pd.concat(paths, ignore_index=True)
    paths.to_csv(out / "pathcheck.csv", index=False)
    text += "\n" + path_report(e, paths)
    text += (
        f"\nFigures: seed {FIGURE_SEED} (numpy default_rng), two drawn without replacement from the {int((pool['enough_type'] == 'redirect').sum())} "
        f"redirect balls, then two from the {int((pool['enough_type'] == 'move').sum())} move balls, each pool sorted by match and seq_i.\n\n"
        + md(pd.DataFrame(figures).sort_values("figure"), ".2f")
        + "\n"
    )  # fmt: skip
    (out / "report.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "")
