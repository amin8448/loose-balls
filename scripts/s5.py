"""S5: dry run of V1 to V3 and the MT1 report-only items on the exploration analysis set.

A bug check, not a test: the frozen parameters were fitted on these episodes. Writes
audit/s5_episodes_exploration.csv (per-episode probabilities, shares and verdicts) and
audit/s5_clips_exploration.csv (the clip export).
"""

import numpy as np
import pandas as pd
from step2_common import analysis_set, bootstrap_within_match, episode_table, load_frozen, probabilities

from looseball_research import decompose, export_clips, io, paths
from looseball_research import expectation as ex

VARIANTS = {
    "anchor 0.2 s later": {"anchor_shift": 2},
    "growing radius max(15 m, 8 m/s x lead)": {"growing_speed": 8.0},
    "pleuler turning penalty": {"turning_penalty": "pleuler"},
    "smoothing window 7": {"window": 7},
    "extrapolated players dropped": {"drop_extrapolated": True},
    "reaction time 0.35 s": {"reaction_time": 0.35},
}
N_BOOT, SEED = 2000, 0


def md(t: pd.DataFrame, floatfmt: str = ".3f") -> str:
    return t.to_markdown(index=False, floatfmt=floatfmt)


def aligned(keys: pd.DataFrame, **settings) -> pd.DataFrame:
    v = episode_table(keys=keys, **settings).set_index(["match_id", "seq_i"])
    return v.loc[list(zip(keys["match_id"], keys["seq_i"]))].reset_index()


def decomposed(t: pd.DataFrame, p: pd.DataFrame) -> pd.DataFrame:
    """Decompose with the base leads (no episode turns immediate under a variant)."""
    return decompose.decompose(
        p["p_static"], p["p_dynamic"], t["releasing_won"], t["lead2_s"].clip(lower=0.5)
    )


def comparison(t: pd.DataFrame, a: str, b: str) -> dict:
    """Log-loss of probability column b minus that of a: positive means a is better."""
    y = t["releasing_won"]

    def stat(d):
        return ex.log_loss(d["releasing_won"], d[b]) - ex.log_loss(d["releasing_won"], d[a])

    boot = bootstrap_within_match(t, stat, N_BOOT, SEED)
    per_match = {m: stat(d) for m, d in t.groupby("match_id")}
    return {
        "model": a,
        "comparison": b,
        "log-loss model": ex.log_loss(y, t[a]),
        "log-loss comparison": ex.log_loss(y, t[b]),
        "difference": stat(t),
        "lo": np.quantile(boot, 0.025),
        "hi": np.quantile(boot, 0.975),
        "interval excludes 0": bool(np.quantile(boot, 0.025) > 0 or np.quantile(boot, 0.975) < 0),
        "matches with the same direction (of 5)": int(sum(v > 0 for v in per_match.values())),
    }


def main() -> None:
    frozen = load_frozen()
    base = episode_table()
    t = analysis_set(base)
    p = probabilities(t, frozen)
    t = pd.concat([t, p], axis=1)
    d = decomposed(t, p)
    t = pd.concat([t, d], axis=1)
    t["losing_team"] = np.where(t["releasing_won"] == 1, _other_team(t), t["team_id_i"])
    t["winning_team"] = t["team_id_next"]
    print(f"dry run on the exploration analysis set: {len(t)} episodes (bug check, not a test)\n")

    print(
        "V1 and V2 (dry run). Differences are log-loss of the comparison minus log-loss of the better-expected model:\n"
    )
    rows = [
        comparison(t, "p_dynamic", "p_B0"),
        comparison(t, "p_dynamic", "p_B1"),
        comparison(t, "p_dynamic", "p_static"),
    ]
    v12 = pd.DataFrame(rows)
    v12.insert(0, "check", ["V1 against B0", "V1 against B1", "V2 against p_static"])
    print(md(v12, ".4f"))

    print(
        "\nV3 (dry run). Verdicts of lost balls unchanged under each variant on its own (frozen D5 parameter, base set fixed):\n"
    )
    rows = []
    for name, kw in VARIANTS.items():
        v = aligned(t, **kw)
        pv = probabilities(v, frozen)
        dv = decomposed(t, pv)
        same = (dv["verdict"].to_numpy() == t["verdict"].to_numpy()).mean()
        rows.append(
            {"variant": name, "lost balls": len(t), "verdict unchanged": same, "at least 0.70": same >= 0.70}
        )
    print(md(pd.DataFrame(rows)))

    print("\nCamera gate (dry run, anchored main pairs):\n")
    rate = {w: (~base.loc[base["releasing_won"] == w, "kept"]).mean() for w in (1, 0)}
    print(md(pd.DataFrame([{"anchored pairs": len(base), "dropped": int((~base["kept"]).sum()),
                            "drop share": (~base["kept"]).mean(), "at most 0.30": (~base["kept"]).mean() <= 0.30,
                            "drop rate, releasing team won": rate[1], "drop rate, other team won": rate[0],
                            "difference": rate[1] - rate[0]}])))  # fmt: skip

    print("\nReport-only (dry run). Calibration of p_dynamic, frozen parameter, five bins:\n")
    print(md(ex.calibration(t["p_dynamic"], t["releasing_won"])))

    print("\nReport-only (dry run). Mean deficit shares of the losing team by trigger:\n")
    cols = [f"deficit {s}" for s in decompose.SHARES]
    g = t.groupby("trigger")[cols].mean().reset_index()
    g.insert(1, "lost balls", t.groupby("trigger").size().to_numpy())
    g = pd.concat(
        [g, pd.DataFrame([{"trigger": "all", "lost balls": len(t), **t[cols].mean().to_dict()}])],
        ignore_index=True,
    )
    print(md(g))

    print("\nReport-only (dry run). Share of lost loose balls under each verdict, pooled over teams:\n")
    vc = t["verdict"].value_counts().reindex(list(decompose.SHARES), fill_value=0)
    print(
        md(pd.DataFrame({"verdict": vc.index, "lost balls": vc.to_numpy(), "share": vc.to_numpy() / len(t)}))
    )

    print("\nReport-only (dry run). Constant-acceleration model against the DataBallPy model:\n")
    ca = aligned(t, model_name="constant_acceleration")
    pca = probabilities(ca, {**frozen, "chosen": frozen["constant_acceleration"]})
    dca = decomposed(t, pca)
    print(md(pd.DataFrame([{"log-loss DataBallPy p_dynamic": ex.log_loss(t["releasing_won"], t["p_dynamic"]),
                            "log-loss constant-acceleration p_dynamic": ex.log_loss(t["releasing_won"], pca["p_dynamic"]),
                            "verdicts that agree": (dca["verdict"].to_numpy() == t["verdict"].to_numpy()).mean()}]), ".4f"))  # fmt: skip

    names = team_names()
    ts = decompose.team_shares(t[["match_id", "losing_team", "winning_team", *cols, *[f"credit {s}" for s in decompose.SHARES]]],
                               n_boot=N_BOOT, seed=SEED)  # fmt: skip
    ts.insert(1, "team name", ts["team"].map(names))
    print(
        "\nTeam shares (dry run): deficit over lost balls, credit over won balls, 95% bootstrap intervals within match:\n"
    )
    show = ["team name", "lost", "won"] + [
        c for s in decompose.SHARES for c in (f"deficit {s}", f"deficit {s} lo", f"deficit {s} hi")
    ]
    print(md(ts[show]))
    ts.to_csv(paths.AUDIT_DIR / "s5_team_shares_exploration.csv", index=False, float_format="%.4f")

    clocks = {m: export_clips.match_clock(m) for m in t["match_id"].unique()}
    clips = export_clips.export_clips(
        t.assign(period=t["period_i"], frame=t["anchor_frame"], team=t["losing_team"]), clocks
    )
    clips.to_csv(paths.AUDIT_DIR / "s5_clips_exploration.csv", index=False)
    print(f"\nclips: audit/s5_clips_exploration.csv ({len(clips)} rows); first rows:\n")
    print(md(clips.head(3)))
    keep = ["match_id", "seq_i", "trigger", "anchor_frame", "pickup_frame", "lead_s", "releasing_won", "p_static",
            "p_dynamic", "p_B0", "p_B1", "losing_team", "winning_team", *cols, "verdict"]  # fmt: skip
    t[keep].to_csv(paths.AUDIT_DIR / "s5_episodes_exploration.csv", index=False, float_format="%.4f")


def team_names() -> dict:
    out = {}
    for m in paths.EXPLORATION:
        meta = io.load_metadata(m)
        for side in ("home_team", "away_team"):
            out[meta[side]["id"]] = meta[side]["short_name"]
    return out


def _other_team(t: pd.DataFrame) -> pd.Series:
    """The team that is not the releasing team in each episode's match."""
    teams = {}
    for m in t["match_id"].unique():
        meta = io.load_metadata(int(m))
        teams[m] = (meta["home_team"]["id"], meta["away_team"]["id"])
    return pd.Series([teams[m][0] if teams[m][1] == r else teams[m][1] for m, r in zip(t["match_id"], t["team_id_i"])],
                     index=t.index)  # fmt: skip


if __name__ == "__main__":
    main()
