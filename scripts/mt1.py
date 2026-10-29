"""MT1, the main test: gates V1 to V3 and the camera gate, then the report-only items.

Usage: python mt1.py exploration   (rehearsal, bug check)
       python mt1.py test          (once, after the MT1 marker is committed)

Frozen parameters come from audit/frozen_parameters.json; nothing is fitted here. Tables go to
stdout; per-episode and per-team tables to audit/mt1_<set>/.
"""

import json
import sys

import numpy as np
import pandas as pd
from step2_common import analysis_set, bootstrap_within_match, episode_table, load_frozen, probabilities

from looseball_research import decompose, export_clips, gate, io, paths, race, velocities
from looseball_research import expectation as ex

VARIANTS = {
    "anchor 0.2 s later": {"anchor_shift": 2},
    "growing radius max(radius, 8 m/s x lead)": {"growing_speed": 8.0},
    "pleuler turning penalty": {"turning_penalty": "pleuler"},
    "smoothing window 7": {"window": 7},
    "extrapolated players dropped": {"drop_extrapolated": True},
    "reaction time 0.35 s": {"reaction_time": 0.35},
}
N_BOOT, SEED = 2000, 0
RADIUS, FALLBACK_RADIUS = 15.0, 10.0
GATE_MAX_DROP, V3_MIN, MATCHES_MIN_TEST = 0.30, 0.70, 10
NEWCASTLE = 1805  # team id of Newcastle United Jets FC (exploration metadata, match 1886347)
SHARE_COLS = [f"deficit {s}" for s in decompose.SHARES]
CREDIT_COLS = [f"credit {s}" for s in decompose.SHARES]


def md(t: pd.DataFrame, floatfmt: str = ".4f") -> str:
    return t.to_markdown(index=False, floatfmt=floatfmt)


def team_info(matches) -> tuple[dict, dict, dict]:
    names, n_matches, opponent = {}, {}, {}
    for m in matches:
        meta = io.load_metadata(m)
        h, a = meta["home_team"]["id"], meta["away_team"]["id"]
        names[h], names[a] = meta["home_team"]["short_name"], meta["away_team"]["short_name"]
        for team in (h, a):
            n_matches[team] = n_matches.get(team, 0) + 1
        opponent[(m, h)], opponent[(m, a)] = a, h
    return names, n_matches, opponent


def with_measures(t: pd.DataFrame, frozen: dict, opponent: dict) -> pd.DataFrame:
    p = probabilities(t, frozen)
    d = decompose.decompose(p["p_static"], p["p_dynamic"], t["releasing_won"], t["lead_s"])
    t = pd.concat([t.reset_index(drop=True), p.reset_index(drop=True), d], axis=1)
    other = [opponent[(m, r)] for m, r in zip(t["match_id"], t["team_id_i"])]
    t["losing_team"] = np.where(t["releasing_won"] == 1, other, t["team_id_i"])
    t["winning_team"] = t["team_id_next"]
    return t


def aligned(keys: pd.DataFrame, matches, **settings) -> pd.DataFrame:
    v = episode_table(keys=keys, matches=matches, **settings).set_index(["match_id", "seq_i"])
    return v.loc[list(zip(keys["match_id"], keys["seq_i"]))].reset_index()


def comparison(t: pd.DataFrame, a: str, b: str, n_matches: int, which: str) -> dict:
    """Log-loss of b minus log-loss of a (positive: a is better), interval and per-match direction."""

    def stat(d):
        return ex.log_loss(d["releasing_won"], d[b]) - ex.log_loss(d["releasing_won"], d[a])

    boot = bootstrap_within_match(t, stat, N_BOOT, SEED)
    lo, hi = np.quantile(boot, 0.025), np.quantile(boot, 0.975)
    same = int(sum(stat(d) > 0 for _, d in t.groupby("match_id")))
    passed = bool(lo > 0 and (which != "test" or same >= MATCHES_MIN_TEST))
    return {
        "comparison": b,
        "log-loss p_dynamic": ex.log_loss(t["releasing_won"], t[a]),
        "log-loss comparison": ex.log_loss(t["releasing_won"], t[b]),
        "difference": stat(t),
        "lo": lo,
        "hi": hi,
        f"matches p_dynamic lower (of {n_matches})": same,
        "result": "pass" if passed else "fail",
    }


def verdict_shares(t: pd.DataFrame) -> pd.Series:
    return t["verdict"].value_counts(normalize=True).reindex(list(decompose.SHARES), fill_value=0.0)


def team_verdict_shares(t: pd.DataFrame, names: dict, n_matches: dict) -> pd.DataFrame:
    teams = sorted(t["losing_team"].unique())

    def shares(d):
        return {
            (team, v): (d.loc[d["losing_team"] == team, "verdict"] == v).mean()
            for team in teams
            for v in decompose.SHARES
        }

    point = shares(t)
    boot = pd.DataFrame(list(bootstrap_within_match(t, shares, N_BOOT, SEED)))
    rows = []
    for team in teams:
        row = {
            "team": names[team],
            "matches in the set": n_matches[team],
            "lost": int((t["losing_team"] == team).sum()),
        }
        for v in decompose.SHARES:
            row[v] = point[(team, v)]
            row[f"{v} lo"], row[f"{v} hi"] = boot[(team, v)].quantile(0.025), boot[(team, v)].quantile(0.975)
        rows.append(row)
    return pd.DataFrame(rows)


def s2_check(t: pd.DataFrame) -> pd.DataFrame:
    model = race.ReachModel()
    times = []
    for m, d in t.groupby("match_id"):
        v = velocities.match_velocities(m).set_index(["frame", "player_id"])
        for r in d.itertuples():
            key = (int(r.anchor_frame), r.player_id_next)
            if key not in v.index:
                times.append((r.Index, np.nan))
                continue
            row = v.loc[key]
            pos = np.array([[row["x"], row["y"]]], dtype=float)
            vel = np.nan_to_num(np.array([[row["vx"], row["vy"]]], dtype=float))
            times.append((r.Index, model.reach_times(pos, vel, (r.pickup_x, r.pickup_y))[0]))
    w = pd.DataFrame(times, columns=["i", "t_winner"]).set_index("i")
    return t.join(w).assign(within=lambda d: d["t_winner"] <= d["lead_s"] + 0.3)


def by_trigger(t: pd.DataFrame, fn) -> pd.DataFrame:
    rows = [{"trigger": k, **fn(g)} for k, g in t.groupby("trigger")]
    rows.append({"trigger": "all", **fn(t)})
    return pd.DataFrame(rows)


def main(which: str) -> None:
    matches = paths.TEST if which == "test" else paths.EXPLORATION
    out_dir = paths.AUDIT_DIR / f"mt1_{which}"
    out_dir.mkdir(exist_ok=True)
    frozen = load_frozen()
    names, n_matches, opponent = team_info(matches)
    n_m = len(matches)

    base15 = episode_table(matches=matches)
    base = base15
    drop15 = (~base15["kept"]).mean()
    radius = RADIUS
    if drop15 > GATE_MAX_DROP:  # consequence fixed in the brief
        radius = FALLBACK_RADIUS
        base = episode_table(matches=matches, radius=radius)
    a = with_measures(analysis_set(base), frozen, opponent)
    print(f"MT1 on the {which} matches ({n_m}): anchored main pairs {len(base)}; camera-gate drop share at 15 m "
          f"{drop15:.4f}; radius of the main analysis {radius:.0f} m; analysis set {len(a)} lost balls\n")  # fmt: skip

    print("Gates V1 and V2 (difference: log-loss of the comparison minus log-loss of p_dynamic):\n")
    g12 = pd.DataFrame(
        [
            {"gate": "V1 against B0", **comparison(a, "p_dynamic", "p_B0", n_m, which)},
            {"gate": "V1 against B1", **comparison(a, "p_dynamic", "p_B1", n_m, which)},
            {"gate": "V2 against p_static", **comparison(a, "p_dynamic", "p_static", n_m, which)},
        ]
    )
    print(md(g12))

    print(
        "\nGate V3 (verdict unchanged under each variant on its own; base set fixed; frozen D5 parameter):\n"
    )
    rows, variant_verdicts = [], {}
    for name, kw in VARIANTS.items():
        kw = {"radius": radius, **kw}
        v = aligned(a, matches, **kw)
        pv = probabilities(v, frozen)
        dv = decompose.decompose(pv["p_static"], pv["p_dynamic"], a["releasing_won"], a["lead_s"])
        variant_verdicts[name] = dv["verdict"].to_numpy()
        same = (dv["verdict"].to_numpy() == a["verdict"].to_numpy()).mean()
        rows.append({"variant": name, "lost balls": len(a), "verdict unchanged": same,
                     "result": "pass" if same >= V3_MIN else "fail"})  # fmt: skip
    g3 = pd.DataFrame(rows)
    print(md(g3))

    rate = {w: (~base15.loc[base15["releasing_won"] == w, "kept"]).mean() for w in (1, 0)}
    gc = {
        "anchored pairs": len(base15),
        "dropped at 15 m": int((~base15["kept"]).sum()),
        "drop share at 15 m": drop15,
        "result": "pass" if drop15 <= GATE_MAX_DROP else "fail",
        "drop rate, releasing team won": rate[1],
        "drop rate, other team won": rate[0],
        "difference": rate[1] - rate[0],
    }
    print("\nCamera gate (D7, at most 30% of anchored main pairs dropped):\n")
    print(md(pd.DataFrame([gc])))

    v1 = (g12.loc[:1, "result"] == "pass").all()
    v2 = g12.loc[2, "result"] == "pass"
    v3 = (g3["result"] == "pass").all()
    consequences = pd.DataFrame(
        [
            {"gate": "V1", "result": "pass" if v1 else "fail",
             "consequence": "verdicts reported" if v1 else "audit and descriptives only, no verdicts"},
            {"gate": "V2", "result": "pass" if v2 else "fail",
             "consequence": "reading term kept" if v2 else "reading term dropped: positioning against the race"},
            {"gate": "V3", "result": "pass" if v3 else "fail",
             "consequence": "one verdict label" if v3 else "verdicts shown with their variants, never one label"},
            {"gate": "camera gate", "result": gc["result"],
             "consequence": "15 m radius" if gc["result"] == "pass" else "radius 10 m for the main analysis"},
        ]
    )  # fmt: skip
    print("\nConsequences fixed in the brief:\n")
    print(md(consequences))
    headline_valid = v1 and v2 and v3

    print(
        f"\nR1. Categorical verdict shares of lost loose balls, pooled over teams (headline: {headline_valid}):\n"
    )
    off = with_measures(base[~base["immediate"]].reset_index(drop=True), frozen, opponent)
    r1 = pd.DataFrame({"verdict": list(decompose.SHARES), "gated (D7 on)": verdict_shares(a).to_numpy(),
                       "ungated (D7 off, extrapolated positions kept)": verdict_shares(off).to_numpy()})  # fmt: skip
    print(md(pd.concat([r1, pd.DataFrame([{"verdict": "lost balls", "gated (D7 on)": len(a),
                                           "ungated (D7 off, extrapolated positions kept)": len(off)}])])))  # fmt: skip
    print("\nR2. Gated against ungated, by trigger (share of lost balls under each verdict):\n")
    rows = []
    for label, d in (("gated", a), ("ungated", off)):
        for k, g in d.groupby("trigger"):
            rows.append({"set": label, "trigger": k, "lost balls": len(g), **verdict_shares(g).to_dict()})
    print(md(pd.DataFrame(rows), ".3f"))
    dropped = off[~off["kept"]]
    print(f"\nR2b. The {len(dropped)} lost balls that D7 drops, verdict shares:\n")
    print(md(pd.DataFrame([{"lost balls": len(dropped), **verdict_shares(dropped).to_dict()}]), ".3f"))

    print("\nR3. Continuous deficit shares of the losing team, pooled and by trigger:\n")
    print(md(by_trigger(a, lambda d: {"lost balls": len(d), **d[SHARE_COLS].mean().to_dict()}), ".3f"))

    print("\nR4. Calibration of p_dynamic, five bins:\n")
    print(md(ex.calibration(a["p_dynamic"], a["releasing_won"]), ".3f"))

    base = base.assign(winner=np.where(base["releasing_won"] == 1, "releasing team", "other team"))
    print("\nR5. Immediate class (lead < 0.5 s), anchored main pairs, by trigger and by winner:\n")
    for by in ("trigger", "winner"):
        g = base.groupby(by)["immediate"].agg(episodes="size", immediate="sum", share="mean").reset_index()
        g = pd.concat([g, pd.DataFrame([{by: "all", "episodes": len(base), "immediate": int(base["immediate"].sum()),
                                         "share": base["immediate"].mean()}])])  # fmt: skip
        print(md(g, ".3f"))
        print()

    print("R6. D7 drop rates by trigger and by winner, and the releasing team's win-share difference:\n")
    print(md(gate.drop_rates(base, "trigger"), ".3f"))
    print()
    print(md(gate.drop_rates(base, "winner"), ".3f"))
    print()
    print(md(pd.DataFrame([gate.win_share_difference(base.reset_index(drop=True), N_BOOT, SEED)]), ".3f"))

    print("\nR7. S2 reachability check by trigger (winner reach time <= lead + 0.3 s):\n")
    s2 = s2_check(base)
    for label, d in (("analysis set", s2[s2["kept"] & ~s2["immediate"]]), ("all anchored pairs", s2),
                     ("lead >= 0.5 s", s2[~s2["immediate"]])):  # fmt: skip
        print(f"{label}:\n")
        print(md(by_trigger(d, lambda g: {"episodes": len(g), "share": g["within"].mean(),
                                          "winner not on anchor frame": int(g["t_winner"].isna().sum())}), ".3f"))  # fmt: skip
        print()

    print("R8. Constant-acceleration model (report-only):\n")
    ca = aligned(a, matches, radius=radius, model_name="constant_acceleration")
    pca = probabilities(ca, {**frozen, "chosen": frozen["constant_acceleration"]})
    dca = decompose.decompose(pca["p_static"], pca["p_dynamic"], a["releasing_won"], a["lead_s"])
    print(md(pd.DataFrame([{"log-loss DataBallPy p_dynamic": ex.log_loss(a["releasing_won"], a["p_dynamic"]),
                            "log-loss constant-acceleration p_dynamic": ex.log_loss(a["releasing_won"], pca["p_dynamic"]),
                            "verdicts that agree": (dca["verdict"].to_numpy() == a["verdict"].to_numpy()).mean()}])))  # fmt: skip

    flagged = {t for t, n in n_matches.items() if n <= 2}
    flagged |= {t for t, n in names.items() if t == NEWCASTLE or "Newcastle" in n}
    tv = team_verdict_shares(a, names, n_matches)
    tv.insert(
        1, "sample-size flag", ["flag" if t in flagged else "" for t in sorted(a["losing_team"].unique())]
    )
    print(
        "\nR9a. Team-level categorical verdict shares over lost balls, 95% bootstrap intervals within match:\n"
    )
    print(md(tv, ".3f"))
    tc = decompose.team_shares(
        a[["match_id", "losing_team", "winning_team", *SHARE_COLS, *CREDIT_COLS]], N_BOOT, SEED
    )
    tc.insert(1, "name", tc["team"].map(names))
    tc.insert(2, "matches in the set", tc["team"].map(n_matches))
    tc.insert(3, "sample-size flag", ["flag" if t in flagged else "" for t in tc["team"]])
    show = ["name", "matches in the set", "sample-size flag", "lost", "won"]
    show += [c for s in decompose.SHARES for c in (f"deficit {s}", f"deficit {s} lo", f"deficit {s} hi")]
    print(
        "\nR9b. Team-level continuous deficit shares over lost balls, 95% bootstrap intervals within match:\n"
    )
    print(md(tc[show], ".3f"))

    keep = ["match_id", "seq_i", "trigger", "anchor_frame", "pickup_frame", "lead_s", "releasing_won", "p_static",
            "p_dynamic", "p_B0", "p_B1", "losing_team", "winning_team", *SHARE_COLS, "verdict"]  # fmt: skip
    a[keep].assign(**{f"verdict {k}": v for k, v in variant_verdicts.items()}).to_csv(
        out_dir / "episodes.csv", index=False, float_format="%.4f"
    )
    off[keep + ["kept"]].to_csv(out_dir / "episodes_ungated.csv", index=False, float_format="%.4f")
    tv.to_csv(out_dir / "team_verdicts.csv", index=False, float_format="%.4f")
    tc.to_csv(out_dir / "team_shares.csv", index=False, float_format="%.4f")
    clocks = {m: export_clips.match_clock(m) for m in a["match_id"].unique()}
    export_clips.export_clips(
        a.assign(period=a["period_i"], frame=a["anchor_frame"], team=a["losing_team"]), clocks
    ).to_csv(out_dir / "clips.csv", index=False)
    summary = {"set": which, "matches": n_m, "anchored pairs": len(base), "analysis set": len(a), "radius": radius,
               "V1": bool(v1), "V2": bool(v2), "V3": bool(v3), "camera gate": gc["result"] == "pass"}  # fmt: skip
    (out_dir / "gates.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"\noutputs: audit/mt1_{which}/")


if __name__ == "__main__":
    main(sys.argv[1])
