"""A1. Gap cross-tab of trigger by resolution, split by continuity, and the gap histogram.

Prints markdown tables for AUDIT.md and writes audit/figures/a1_gap_histogram.png.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import MaxNLocator

from looseball import episodes, paths

TRIGGERS = ["T0", "T1", "T2", "T3", "T4", "T5", "T6", "other"]


def gap_stats(g: pd.Series) -> pd.Series:
    s = g.to_numpy() / paths.FPS
    return pd.Series(
        {
            "n": len(s),
            "p10 s": np.quantile(s, 0.1),
            "p50 s": np.quantile(s, 0.5),
            "p90 s": np.quantile(s, 0.9),
            "share gap >= 3 fr": (g >= 3).mean(),
        }
    )


def stats_table(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    rows = []
    for keys, g in df.groupby(by, sort=False):
        keys = keys if isinstance(keys, tuple) else (keys,)
        rows.append({**dict(zip(by, keys)), **gap_stats(g["gap"])})
    t = pd.DataFrame(rows)
    order = {
        "trigger": TRIGGERS,
        "resolution": [*episodes.RESOLUTIONS, "all"],
        "continuity": episodes.CONTINUITY,
    }
    for col in by:
        t[col] = pd.Categorical(t[col], categories=order[col] + (["all"] if "all" not in order[col] else []))
    t = t.sort_values(by).reset_index(drop=True)
    t["n"] = t["n"].astype(int)
    return t


def with_totals(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Rows per (by) cell, a resolution = all row per trigger, and an overall row."""
    parts = [stats_table(df, by)]
    parts.append(stats_table(df.assign(resolution="all"), by))
    t = pd.concat(parts, ignore_index=True)
    for col in by:
        t[col] = pd.Categorical(t[col], categories=parts[0][col].cat.categories)
    t = t.sort_values(by).reset_index(drop=True)
    total = {c: "all" for c in by} | gap_stats(df["gap"]).to_dict()
    t = pd.concat([t.astype({c: str for c in by}), pd.DataFrame([total])], ignore_index=True)
    t["n"] = t["n"].astype(int)
    return t


def md(t: pd.DataFrame) -> str:
    fmt = [".3f" if c.startswith("share") else ".2f" for c in t.columns]
    return t.to_markdown(index=False, floatfmt=fmt)


def histogram(r: pd.DataFrame, path) -> None:
    surface, ink, muted, grid, series = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6"
    fig, axes = plt.subplots(2, 4, figsize=(14, 6.2), sharex=True, facecolor=surface)
    bins = np.arange(-0.5, 51.5, 1)
    for ax, t in zip(axes.flat, TRIGGERS):
        g = r.loc[r["trigger"] == t, "gap"]
        ax.set_facecolor(surface)
        ax.hist(g.clip(upper=60), bins=bins, color=series, edgecolor=surface, linewidth=0.8)
        ax.axvline(2.5, color=muted, linestyle=(0, (3, 3)), linewidth=0.8)
        ax.set_title(
            f"{episodes.TRIGGER_LABELS[t]}\nn = {len(g)}, above 50 fr: {(g > 50).sum()}",
            fontsize=9.5,
            color=ink,
            loc="left",
        )
        ax.grid(axis="y", color=grid, linewidth=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(grid)
        ax.tick_params(colors=muted, labelsize=8)
        ax.set_xlim(-0.5, 50.5)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    for ax in axes[1]:
        ax.set_xlabel("gap (frames, 10 per second)", fontsize=8.5, color=muted)
    for ax in axes[:, 0]:
        ax.set_ylabel("retained pairs", fontsize=8.5, color=muted)
    fig.suptitle(
        "A1. Gap from release to pickup by trigger class, retained pairs, five exploration matches. "
        "Right of the dashed line: gap >= 3 frames.",
        fontsize=10.5,
        color=ink,
        x=0.01,
        ha="left",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=150, facecolor=surface)


def main() -> None:
    p = episodes.all_pairs()

    drops = p.groupby("match_id", sort=False).agg(
        pairs=("retained", "size"),
        period=("drop_period", "sum"),
        restart=("drop_restart", "sum"),
        offside=("drop_offside", "sum"),
        stoppage=("drop_interruption", "sum"),
        retained=("retained", "sum"),
    )
    drops["dropped"] = drops["pairs"] - drops["retained"]
    drops.loc["total"] = drops.sum()
    print("Drop reasons (a pair can carry more than one):\n")
    print(drops.reset_index().to_markdown(index=False))

    r = p[p["retained"]].copy()
    print("\nA1a. Retained pairs, trigger by resolution, counts:\n")
    ct = pd.crosstab(
        pd.Categorical(r["trigger"], TRIGGERS),
        pd.Categorical(r["resolution"], episodes.RESOLUTIONS),
        margins=True,
        margins_name="all",
        dropna=False,
    )
    ct.index.name, ct.columns.name = "trigger", None
    print(ct.reset_index().to_markdown(index=False))

    print("\nA1b. Retained pairs, gap quantiles (seconds) and share with gap >= 3 frames, by cell:\n")
    print(md(with_totals(r, ["trigger", "resolution"])))

    print("\nA1c. Counts by continuity and trigger:\n")
    cc = pd.crosstab(
        pd.Categorical(r["trigger"], TRIGGERS),
        pd.Categorical(r["continuity"], episodes.CONTINUITY),
        margins=True,
        margins_name="all",
        dropna=False,
    )
    cc.index.name, cc.columns.name = "trigger", None
    print(cc.reset_index().to_markdown(index=False))

    for c in episodes.CONTINUITY:
        print(f"\nA1d. Continuity = {c}: gap quantiles (seconds) and share with gap >= 3 frames, by cell:\n")
        print(md(with_totals(r[r["continuity"] == c], ["trigger", "resolution"])))

    cand = r[r["candidate"]]
    loose_trigger = cand["trigger"].isin(episodes.LOOSE_TRIGGERS)
    loose_res = cand["resolution"].isin(["recovery", "unknown"])
    print("\nA1e. Candidate episodes under the provisional definition:\n")
    route = pd.DataFrame(
        {
            "route": [
                "trigger T1 to T6 only",
                "resolution recovery or unknown only",
                "both",
                "all candidates",
            ],
            "pairs": [
                int((loose_trigger & ~loose_res).sum()),
                int((~loose_trigger & loose_res).sum()),
                int((loose_trigger & loose_res).sum()),
                len(cand),
            ],
        }
    )
    print(route.to_markdown(index=False))
    in_scope = r["trigger"].isin(episodes.LOOSE_TRIGGERS) | r["resolution"].isin(["recovery", "unknown"])
    excl = pd.DataFrame(
        {
            "retained pairs meeting the trigger or resolution rule": [int(in_scope.sum())],
            "excluded as same player": [int((in_scope & (r["continuity"] == "same player")).sum())],
            "excluded for gap < 1 frame": [int((in_scope & (r["gap"] < 1)).sum())],
            "candidates": [len(cand)],
        }
    )
    print()
    print(excl.to_markdown(index=False))
    print("\nA1f. Candidates, gap in frames by bucket, by trigger and resolution (cells with n >= 5):\n")
    buckets = pd.cut(
        cand["gap"], [0, 1, 2, 5, 10, 30, np.inf], labels=["1", "2", "3-5", "6-10", "11-30", ">30"]
    )
    gb = pd.crosstab([cand["trigger"], cand["resolution"]], buckets)
    gb = gb[gb.sum(axis=1) >= 5]
    gb.columns = [f"gap {c} fr" for c in gb.columns]
    print(gb.reset_index().to_markdown(index=False))

    print("\nA1g. Candidates where the player of possession i+1 is the goalkeeper (player_position GK):\n")
    gk = (
        cand.assign(gk=cand["player_position_next"].eq("GK"))
        .groupby(["trigger", "resolution"])["gk"]
        .agg(candidates="size", goalkeeper="sum")
        .reset_index()
    )
    print(gk[gk["goalkeeper"] > 0].to_markdown(index=False))

    print("\nCandidates by match:\n")
    print(cand.groupby("match_id").size().rename("candidates").reset_index().to_markdown(index=False))

    print("\nLong gaps among retained pairs, by trigger:\n")
    lg = (
        r.assign(
            **{
                "gap > 5 s": r["gap"] > 50,
                "gap > 10 s": r["gap"] > 100,
                "gap > 30 s": r["gap"] > 300,
            }
        )
        .groupby(pd.Categorical(r["trigger"], TRIGGERS), observed=False)[
            ["gap > 5 s", "gap > 10 s", "gap > 30 s"]
        ]
        .sum()
    )
    lg.loc["all"] = lg.sum()
    lg.index.name = "trigger"
    lg["max gap s"] = list(
        r.groupby(pd.Categorical(r["trigger"], TRIGGERS), observed=False)["gap"].max() / 10
    ) + [r["gap"].max() / 10]
    print(lg.reset_index().to_markdown(index=False, floatfmt=".1f"))

    print("\nA1h. All retained pairs with resolution unknown:\n")
    u = r.loc[
        r["resolution"] == "unknown", ["match_id", "seq_i", "trigger", "continuity", "gap", "candidate"]
    ]
    print(
        u.sort_values("gap")
        .assign(**{"gap s": u["gap"] / paths.FPS})
        .to_markdown(index=False, floatfmt=".1f")
    )
    print(
        f"max gap of retained pairs with another resolution: {r.loc[r['resolution'] != 'unknown', 'gap'].max()} frames"
    )

    print("\nA1i. Retained pairs, resolution by continuity:\n")
    rc = pd.crosstab(
        pd.Categorical(r["resolution"], episodes.RESOLUTIONS),
        pd.Categorical(r["continuity"], episodes.CONTINUITY),
        margins=True,
        margins_name="all",
        dropna=False,
    )
    rc.index.name, rc.columns.name = "resolution", None
    print(rc.reset_index().to_markdown(index=False))

    path = paths.FIGURES / "a1_gap_histogram.png"
    histogram(r, path)
    print(f"\nfigure: {path.relative_to(paths.ROOT)}")


if __name__ == "__main__":
    main()
