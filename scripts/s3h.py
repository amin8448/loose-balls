"""Step 3h: what would have been enough, its checks C1 to C7 and the path check P1 to P3b
(report-only; AUDIT.md "3h. What would have been enough", "Path check: procedure" and "3h post
hoc revisions after the exploration rehearsal"; DESIGN.md "3h").

Usage: python scripts/s3h.py SET [OUT]
SET is "exploration" (rehearsal, bug check) or "test" (the 15 test matches, run once). OUT
defaults to audit/s3h_SET. Writes report.md, clips_enough.csv (identical to the one looseball
reproduce writes for the test set), enough_all_sets.csv (the enough and report-only redirection
quantities of the analysis set, the ungated balls and each V3 variant) and pathcheck.csv.

The first exploration rehearsal (2026-11-17, before revision R1) also drew four figures; that
code was removed with R1, and its outputs stay in audit/s3h_exploration/ and audit/figures/.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from looseball.adapters.skillcorner import load_match
from looseball.enough import TIE, TYPES
from looseball.export_clips import export_clips_enough
from looseball.pathcheck import TOLERANCES, path_check
from looseball.race import REACTION, ReachModel
from looseball.report import bootstrap_within_match
from looseball.reproduce import N_BOOT, SEED, TEST_MATCHES, VARIANTS, compute, enough_tables
from looseball.velocities import tracking_velocities

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "opendata"
SETS = {"exploration": (1886347, 1959846, 1996435, 1996436, 2007448), "test": TEST_MATCHES}
LOST = ("positioning", "reading")
KEY = ["match_id", "seq_i"]
BLANK = "blank (after the anchor)"


def md(t: pd.DataFrame, floatfmt: str = ".3f") -> str:
    return t.to_markdown(index=False, floatfmt=floatfmt)


def q(x) -> dict:
    x = pd.Series(x, dtype=float).dropna()
    if x.empty:
        return {"n": 0, "p10": np.nan, "p50": np.nan, "p90": np.nan}
    return {"n": len(x), "p10": x.quantile(0.1), "p50": x.quantile(0.5), "p90": x.quantile(0.9)}


def moved_time(row, race: pd.DataFrame, target, model: ReachModel) -> float:
    """Bug check: the enough player's reach time after the move (frozen model)."""
    p = race[race["column_id"] == row.enough_player].iloc[0]
    pos, vel = np.array([p.x, p.y], float), np.nan_to_num(np.array([p.vx, p.vy], float))
    drift = target - (pos + REACTION * vel)
    return model.tti(pos + row.metres_short * drift / np.hypot(*drift), target, vel)


def checks(r: dict, tabs: dict) -> tuple[str, pd.DataFrame]:
    a = r["a"]
    cols = [
        *KEY,
        "trigger",
        "verdict",
        "loser_side",
        "pickup_x",
        "pickup_y",
        "p_static_loser",
        "p_dynamic_loser",
    ]
    e = a[cols].merge(tabs["a"], on=KEY, validate="1:1")
    e["type"] = e["enough_type"].fillna(BLANK)
    out = [f"3h on {r['n_sets']} matches: {len(e)} lost balls in the analysis set.\n"]

    order = [*TYPES, BLANK]
    out.append("C1. Counts by enough_type, by verdict and by trigger:\n")
    for by in ("verdict", "trigger"):
        c = pd.crosstab(e[by], e["type"], margins=True, margins_name="all").reindex(
            columns=[*order, "all"], fill_value=0
        )
        out.append(md(c.reset_index(), ".0f") + "\n")

    out.append(
        "C2 and C3. metres_short (move balls: D > 0 with a losing player in the race) and, report-only, the "
        "rotation of the smallest redirection (balls where one exists), by verdict:\n"
    )
    rows = []
    for v in LOST:
        d = e[e["verdict"] == v]
        rows.append({"quantity": "metres_short, m", "verdict": v, **q(d["metres_short"])})
        rows.append({"quantity": "redirect_degrees (report-only)", "verdict": v, **q(d["redirect_degrees"])})
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
    fixed = reading["redirect_degrees"].notna()
    out.append(
        f"C4 (report-only). Reading verdicts where one redirection makes the race level: {int(fixed.sum())} of "
        f"{len(reading)} ({fixed.mean():.3f}).\n"
    )
    moves = e[e["enough_type"] == "move"]
    out.append(
        f"C5. Of {len(moves)} move balls: enough player extrapolated at the anchor "
        f"{int(moves['enough_player_extrapolated'].sum())} ({moves['enough_player_extrapolated'].mean():.3f}); "
        f"goalkeeper {int(moves['enough_player_gk'].sum())} ({moves['enough_player_gk'].mean():.3f}).\n"
    )

    out.append(
        "C6. Stability under each V3 variant (positioning and reading balls whose verdict is unchanged):\n"
    )
    rows = []
    base = e[e["verdict"].isin(LOST)].set_index(KEY)
    for name in VARIANTS:
        v = tabs[name].set_index(KEY).reindex(base.index)
        verdicts = pd.Series(r["variant_verdicts"][name], index=pd.MultiIndex.from_frame(a[KEY])).reindex(
            base.index
        )
        same_v = verdicts == base["verdict"]
        b, w = base[same_v], v[same_v]
        same = (b["enough_type"] == w["enough_type"]) & (
            b["enough_player"].fillna("") == w["enough_player"].fillna("")
        )
        move = (b["enough_type"] == "move") & (w["enough_type"] == "move")
        red = b["redirect_degrees"].notna() & w["redirect_degrees"].notna()
        rows.append(
            {
                "variant": name,
                "balls": len(base),
                "left out (verdict changed)": 1 - same_v.mean(),
                "kept": len(b),
                "type and player unchanged": same.mean(),
                "move: n both": int(move.sum()),
                "move: Spearman metres_short": spearmanr(
                    b.loc[move, "metres_short"], w.loc[move, "metres_short"]
                ).statistic
                if move.sum() >= 3
                else np.nan,
                "redirect (report-only): n both": int(red.sum()),
                "redirect: Spearman degrees": spearmanr(
                    b.loc[red, "redirect_degrees"], w.loc[red, "redirect_degrees"]
                ).statistic
                if red.sum() >= 3
                else np.nan,
            }
        )
    out.append(md(pd.DataFrame(rows)) + "\n")

    off = r["off"][[*KEY, "verdict"]].merge(tabs["off"], on=KEY, validate="1:1")
    rows = [
        {
            "verdict": v,
            "ungated lost balls": int((off["verdict"] == v).sum()),
            "median metres_short": off.loc[off["verdict"] == v, "metres_short"].median(),
            "median redirect_degrees (report-only)": off.loc[
                off["verdict"] == v, "redirect_degrees"
            ].median(),
        }
        for v in LOST
    ]
    out.append("C7. Ungated lost balls (D7 off), report-only line:\n")
    out.append(md(pd.DataFrame(rows), ".2f") + "\n")

    model = ReachModel()
    races = dict(tuple(r["reach"].groupby(KEY, sort=False)))
    errs, prec, ties = [], 0, 0
    for row in e[e["verdict"].isin(LOST)].itertuples(index=False):
        race = races[(row.match_id, row.seq_i)]
        losing = race[race["side"] == row.loser_side]
        players = losing[~losing["empty_team"].astype(bool)]
        t_w = race.loc[race["side"] != row.loser_side, "t_dynamic"].min()
        prec += int(row.deficit_s <= 0 and players.empty)
        if not players.empty:
            ties += int((players["t_dynamic"] <= players["t_dynamic"].min() + TIE).sum() > 1)
        if row.enough_type == "move":
            errs.append(abs(moved_time(row, race, np.array([row.pickup_x, row.pickup_y]), model) - t_w))
    out.append(
        f"Diagnostics: the precedence rule (D <= 0 with an empty losing side, typed already_favourite) applied to "
        f"{prec} balls; the best-placed tie rule decided {ties} balls.\n"
    )
    out.append(
        f"Bug check: after the move the best-placed player's reach time equals t_w, so the race is level, for all "
        f"{len(errs)} move balls (largest difference {max(errs) if errs else float('nan'):.2e} s).\n"
    )
    return "\n".join(out), e


def path_report(e: pd.DataFrame, paths: pd.DataFrame) -> str:
    p = e.merge(paths, on=KEY, validate="1:1")
    g = p[p["ground"]].reset_index(drop=True)
    head = (
        f"Path check on {len(p)} lost balls: {len(g)} ground, {len(p) - len(g)} aerial (left out). "
        f"Ball-detected path frames per ground ball: median {g['path_frames'].median():.0f}.\n"
    )
    out = [head]
    frozen = {
        "P1": np.where(
            g["p_dynamic_loser"] > 0.5, "loser", np.where(g["p_dynamic_loser"] < 0.5, "winner", "none")
        ),
        "P1b": g["pickup favourite all players"].to_numpy(),
    }
    labels = {
        "P1": "the frozen dynamic favourite (15 m race)",
        "P1b": "the favourite at the pickup point from all players",
    }
    for tol in TOLERANCES:
        k = f"{tol:g}"
        dyn = g[f"dynamic {k} favourite"].to_numpy()
        for name, fav in frozen.items():
            cat = np.select(
                [fav == "none", dyn == "unreached", dyn == "tie", dyn == fav],
                ["no favourite at the pickup", "path: unreached", "path: tie", "agree"],
                "disagree",
            )
            counts = (
                pd.Series(cat)
                .value_counts()
                .reindex(
                    ["agree", "disagree", "path: tie", "path: unreached", "no favourite at the pickup"],
                    fill_value=0,
                )
            )
            out.append(
                f"{name}, tolerance {k} s. Dynamic path favourite against {labels[name]} "
                f"(share agree {counts['agree'] / len(g):.3f} of {len(g)}):\n"
            )
            out.append(md(counts.rename("balls").rename_axis("category").reset_index(), ".0f") + "\n")
        st = g[f"static {k} favourite"].map(
            {
                "loser": "loser is path favourite",
                "winner": "winner is",
                "tie": "tie",
                "unreached": "unreached",
            }
        )
        tab = pd.crosstab(g["verdict"], st, margins=True, margins_name="all")
        out.append(f"P2, tolerance {k} s. Frozen verdict by the loser's static path status:\n")
        out.append(md(tab.reset_index(), ".0f") + "\n")
        pos = g[g["verdict"] == "positioning"].reset_index(drop=True)
        col = f"static {k} favourite"

        def share(d, col=col):
            return (d[col] == "loser").mean()

        def share_b(d, col=col):
            fav = d[col].isin(["loser", "winner"])
            return (d.loc[fav, col] == "loser").mean() if fav.any() else np.nan

        for label, stat, n_den in (
            ("P3", share, len(pos)),
            ("P3b", share_b, int(pos[col].isin(["loser", "winner"]).sum())),
        ):
            boot = np.array(bootstrap_within_match(pos, stat, N_BOOT, SEED))
            what = "" if label == "P3" else " among those with a path favourite (ties and unreached left out)"
            out.append(
                f"{label}, tolerance {k} s. Positioning verdicts where the loser is the static path favourite{what}: "
                f"{int((pos[col] == 'loser').sum())} of {n_den}, {stat(pos):.3f} "
                f"(95% interval {np.nanquantile(boot, 0.025):.3f} to {np.nanquantile(boot, 0.975):.3f}).\n"
            )
    return "\n".join(out)


def main(name: str, out_dir: str | None) -> None:
    if name not in SETS:
        raise SystemExit(f"set must be one of {sorted(SETS)}")
    matches = SETS[name]
    out = Path(out_dir) if out_dir else ROOT / "audit" / f"s3h_{name}"
    out.mkdir(parents=True, exist_ok=True)
    r = compute(DATA, matches=matches)
    tabs = enough_tables(r)
    text, e = checks(r, tabs)
    a = r["a"]
    export_clips_enough(
        a[["match_id", "seq_i", "losing_team", "verdict"]],
        a[["match_id", "seq_i", "period_id", "anchor_frame"]],
        r["clocks"],
        tabs["a"],
        path=out / "clips_enough.csv",
    )
    pd.concat([t.assign(set=k) for k, t in tabs.items()]).to_csv(
        out / "enough_all_sets.csv", index=False, float_format="%.4f"
    )
    paths = []
    for mid in matches:
        m = load_match(DATA, mid)
        balls = a.loc[
            a["match_id"] == mid,
            [
                *KEY,
                "release_frame",
                "anchor_frame",
                "pickup_frame",
                "pickup_x",
                "pickup_y",
                "losing_team",
                "winning_team",
            ],
        ]
        paths.append(path_check(balls, m.tracking, tracking_velocities(m.tracking), m.players))
    paths = pd.concat(paths, ignore_index=True)
    paths.to_csv(out / "pathcheck.csv", index=False, float_format="%.4f")
    text += "\n" + path_report(e, paths)
    (out / "report.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "", sys.argv[2] if len(sys.argv) > 2 else None)
