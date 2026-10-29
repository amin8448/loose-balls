"""S1 (velocity sanity) and S2 (reachability sanity) on the exploration episodes.

Prints markdown tables for AUDIT.md. Procedure logged in AUDIT.md before the run.
"""

import numpy as np
import pandas as pd

from looseball import episodes, gate, paths, race, velocities

TRIGGERS = list(episodes.LOOSE_TRIGGERS)


def md(t: pd.DataFrame, floatfmt: str = ".3f") -> str:
    return t.to_markdown(index=False, floatfmt=floatfmt)


def grouped(df: pd.DataFrame, fn) -> pd.DataFrame:
    rows = [{"trigger": t, **fn(df[df["trigger"] == t])} for t in TRIGGERS if (df["trigger"] == t).any()]
    rows.append({"trigger": "all", **fn(df)})
    return pd.DataFrame(rows)


def races() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ep = episodes.all_episodes()
    main = ep[ep["main"] & ep["anchor2_frame"].notna()].copy()
    summaries, players = [], []
    for m, d in main.groupby("match_id"):
        s, p = race.episode_races(m, d)
        summaries.append(s)
        players.append(p)
    summary = pd.concat(summaries, ignore_index=True)
    keep_cols = ["match_id", "seq_i", "trigger", "pickup_frame", "pickup_x", "pickup_y", "player_id_next"]
    keep_cols += ["winner_detected_pickup"]
    summary = summary.merge(main[keep_cols], on=["match_id", "seq_i"], validate="one_to_one")
    summary["kept"] = gate.keep(
        summary["n_releasing"] + summary["n_other"],
        summary["n_detected_releasing"] + summary["n_detected_other"],
        summary["winner_detected_pickup"],
    )
    summary["immediate"] = summary["lead_s"] < 0.5
    return main, summary, pd.concat(players, ignore_index=True)


def s1(summary: pd.DataFrame, players: pd.DataFrame) -> None:
    print("S1a. Smoothed speed (window 5, order 2) on detected player-frames, all frames of each match:\n")
    rows, pooled = [], []
    for m in [*paths.EXPLORATION, "all"]:
        if m == "all":
            d_speed = pd.concat(pooled, ignore_index=True)
            n_frames = sum(r["detected player-frames"] for r in rows)
        else:
            v = velocities.match_velocities(m)
            d = v[v["is_detected"].fillna(False).astype(bool)]
            d_speed, n_frames = d["speed"], len(d)
            pooled.append(d_speed)
        s = d_speed.dropna()
        rows.append(
            {
                "match": m,
                "detected player-frames": n_frames,
                "with a velocity": len(s),
                "p50 m/s": s.quantile(0.5),
                "p99 m/s": s.quantile(0.99),
                "p99.9 m/s": s.quantile(0.999),
                "max m/s": s.max(),
                "frames > 10 m/s": int((s > 10).sum()),
                "share > 10 m/s": (s > 10).mean(),
            }
        )
    print(md(pd.DataFrame(rows), ".5f"))

    print("\nS1b. Players in the race (15 m) on the last-leg anchor frame, anchored main pairs:\n")
    p = players.merge(summary[["match_id", "seq_i", "trigger"]], on=["match_id", "seq_i"])

    def f(d):
        return {
            "players": len(d),
            "share extrapolated (is_detected FALSE)": (~d["is_detected"]).mean(),
            "share without a velocity": d["velocity_missing"].mean(),
            "share goalkeepers": d["is_gk"].mean(),
        }

    print(md(grouped(p, f)))


def s2(summary: pd.DataFrame) -> None:
    model = race.ReachModel()
    t_win = []
    for m, d in summary.groupby("match_id"):
        v = velocities.match_velocities(m).set_index(["frame", "player_id"])
        for r in d.itertuples():
            key = (int(r.anchor_frame), r.player_id_next)
            if key not in v.index:
                t_win.append((r.Index, np.nan, np.nan))
                continue
            row = v.loc[key]
            vel = np.nan_to_num(np.array([row["vx"], row["vy"]], dtype=float))
            pos = np.array([row["x"], row["y"]], dtype=float)
            t = model.reach_times(pos[None], vel[None], (r.pickup_x, r.pickup_y))[0]
            t_win.append((r.Index, t, np.hypot(*(pos - (r.pickup_x, r.pickup_y)))))
    w = pd.DataFrame(t_win, columns=["i", "t_winner", "d_winner"]).set_index("i")
    s = summary.join(w)
    s["within"] = s["t_winner"] <= s["lead_s"] + 0.3

    def f(d):
        gap = d["t_winner"] - d["lead_s"]
        return {
            "episodes": len(d),
            "winner not on anchor frame": int(d["t_winner"].isna().sum()),
            "share reach <= lead + 0.3 s": d["within"].mean(),
            "winner distance p50 m": d["d_winner"].median(),
            "reach minus lead p10 s": gap.quantile(0.1),
            "reach minus lead p50 s": gap.quantile(0.5),
            "reach minus lead p90 s": gap.quantile(0.9),
        }

    sets = (
        ("S2a. Analysis set (anchored, kept by D7, lead >= 0.5 s), headline", s[s["kept"] & ~s["immediate"]]),
        ("S2b. All anchored main pairs", s),
        ("S2c. Anchored main pairs with lead >= 0.5 s", s[~s["immediate"]]),
    )
    for title, d in sets:
        print(f"\n{title}:\n")
        print(md(grouped(d, f)))

    a = sets[0][1].copy()
    a["lead band s"] = pd.cut(a["lead_s"], [0.5, 1.0, 1.5, 2.0, np.inf], right=False,
                              labels=["0.5 to 1.0", "1.0 to 1.5", "1.5 to 2.0", "2.0 or more"])  # fmt: skip
    a["group"] = np.select([a["trigger"] == "T1", a["trigger"] == "T4"], ["T1", "T4"], "other triggers")
    print(
        "\nS2d. Analysis set: share with reach <= lead + 0.3 s by lead band, for T1, T4 and the other triggers:\n"
    )
    g = (
        a.groupby(["group", "lead band s"], observed=False)["within"]
        .agg(episodes="size", share="mean")
        .reset_index()
    )
    print(md(g))
    print("\nS2e. Analysis set: median lead by trigger:\n")
    print(md(grouped(a, lambda d: {"episodes": len(d), "median lead s": d["lead_s"].median()}), ".2f"))


def main() -> None:
    _, summary, players = races()
    print(f"anchored main pairs: {len(summary)}; kept by D7: {int(summary['kept'].sum())}; "
          f"immediate: {int(summary['immediate'].sum())}; analysis set: {int((summary['kept'] & ~summary['immediate']).sum())}\n")  # fmt: skip
    s1(summary, players)
    s2(summary)


if __name__ == "__main__":
    main()
