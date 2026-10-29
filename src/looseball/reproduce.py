"""looseball reproduce: regenerate every MT1 table from the SkillCorner open-data clone.

The main test MT1 (AUDIT.md, "MT1, the main-test plan") ran once on 15 held-out matches. This
module regenerates its tables through the public API with the frozen parameters shipped in the
package: it recomputes the measures, it does not refit or re-decide anything. Output, in --out:
report.md (every MT1 table, as logged), episodes.csv, episodes_ungated.csv, team_verdicts.csv,
team_shares.csv, clips.csv and gates.json, matching audit/mt1_test; and figures/ (looseball.figures).
"""

import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

from looseball import decompose, expectations, export_clips, find_episodes, reach_times, team_report
from looseball.adapters.skillcorner import load_match
from looseball.decompose import SHARES
from looseball.expectation import baselines, calibration, frozen_parameters, log_loss
from looseball.export_clips import match_clock
from looseball.race import ReachModel
from looseball.report import bootstrap_within_match
from looseball.velocities import tracking_velocities

TEST_MATCHES = (
    1874553, 1899585, 1925299, 1927964, 1953632, 1986691, 2006229, 2006363,
    2007721, 2010085, 2011166, 2013725, 2015213, 2016236, 2017461,
)  # fmt: skip
VARIANTS = {
    "anchor 0.2 s later": {"anchor_shift": 2},
    "growing radius max(radius, 8 m/s x lead)": {"growing_speed": 8.0},
    "pleuler turning penalty": {"turning_penalty": "pleuler"},
    "smoothing window 7": {"smoothing_window": 7},
    "extrapolated players dropped": {"drop_extrapolated": True},
    "reaction time 0.35 s": {"reaction": 0.35},
}
N_BOOT, SEED = 2000, 0
RADIUS, FALLBACK_RADIUS = 15.0, 10.0
GATE_MAX_DROP, V3_MIN, MATCHES_MIN = 0.30, 0.70, 10
NEWCASTLE = 1805  # team id of Newcastle United Jets FC; MT1 flags it for sample size
DEFICIT = [f"deficit {s}" for s in SHARES]
CREDIT = [f"credit {s}" for s in SHARES]


def md(t: pd.DataFrame, floatfmt: str = ".4f") -> str:
    return t.to_markdown(index=False, floatfmt=floatfmt)


def _measures(ep: pd.DataFrame, reach: pd.DataFrame, parameters: dict) -> pd.DataFrame:
    """Per episode: releasing team's p_static, p_dynamic, baselines and the decomposition."""
    e = expectations(reach, parameters)
    out = decompose(e, ep[["match_id", "seq_i"]].assign(winning_team=ep["team_id_next"].to_numpy()))
    out = out.drop(columns=["immediate"])  # the episode table carries the immediate flag
    return out.merge(baselines(reach, parameters), on=["match_id", "seq_i"], validate="1:1")


def _winner_reach(ep: pd.DataFrame, tracking: pd.DataFrame, players: pd.DataFrame) -> pd.Series:
    """S2: the winner's reach time from his state on the anchor frame (shaw, defaults)."""
    vel = tracking_velocities(tracking).set_index(["frame", "column_id"])
    column_of = players.set_index("id")["column_id"]
    model = ReachModel()
    out = []
    for r in ep.itertuples():
        key = (int(r.anchor_frame), column_of.get(r.player_id_next, f"unknown_{r.player_id_next}"))
        if key not in vel.index:
            out.append(np.nan)
            continue
        row = vel.loc[key]
        pos = np.array([[row["x"], row["y"]]], dtype=float)
        v = np.nan_to_num(np.array([[row["vx"], row["vy"]]], dtype=float))
        out.append(model.reach_times(pos, v, (r.pickup_x, r.pickup_y))[0])
    return pd.Series(out, index=ep.index)


def compute(data, matches=TEST_MATCHES) -> dict:
    """Every per-episode quantity MT1 needs, match by match."""
    frozen = frozen_parameters()
    ca_parameters = {**frozen, "chosen": frozen["constant_acceleration"]}
    names, n_matches, eps15 = {}, {}, []
    for mid in matches:
        m = load_match(data, mid)
        names.update(m.team_names)
        for team in (m.home_team_id, m.away_team_id):
            n_matches[team] = n_matches.get(team, 0) + 1
        eps15.append(find_episodes(m.possessions, m.tracking, m.players, radius=RADIUS))
    ep15 = pd.concat(eps15, ignore_index=True)
    anchored15 = ep15[ep15["anchored"]]
    drop15 = (~anchored15["kept"]).mean()
    radius = RADIUS if drop15 <= GATE_MAX_DROP else FALLBACK_RADIUS  # consequence fixed in the brief

    bases, variants, cas, clocks = [], [], [], {}
    for mid in matches:
        m = load_match(data, mid)
        clocks[mid] = match_clock(m.tracking)
        ep = find_episodes(m.possessions, m.tracking, m.players, radius=radius)
        ep = ep[ep["anchored"]].reset_index(drop=True)
        reach = reach_times(ep, m.tracking, m.players, radius=radius)
        meas = _measures(ep, reach, frozen)
        base = ep.merge(meas, on=["match_id", "seq_i"], validate="1:1")
        base["t_winner"] = _winner_reach(ep, m.tracking, m.players).to_numpy()
        bases.append(base)
        a = base[base["kept"] & ~base["immediate"]]
        for name, kw in VARIANTS.items():
            r = reach_times(a, m.tracking, m.players, radius=radius, **kw)
            variants.append(_measures(a, r, frozen)[["match_id", "seq_i", "verdict"]].assign(variant=name))
        r = reach_times(a, m.tracking, m.players, radius=radius, model="constant_acceleration")
        cas.append(_measures(a, r, ca_parameters)[["match_id", "seq_i", "p_dynamic", "verdict"]])
    base = (
        pd.concat(bases, ignore_index=True)
        .sort_values(["match_id", "seq_i"], kind="stable")
        .reset_index(drop=True)
    )
    base["releasing_won"] = (base["team_id_next"] == base["team_id_i"]).astype(int)
    a = base[base["kept"] & ~base["immediate"]].reset_index(drop=True)
    off = base[~base["immediate"]].reset_index(drop=True)
    var = pd.concat(variants, ignore_index=True)
    ca = pd.concat(cas, ignore_index=True)
    key = ["match_id", "seq_i"]
    variant_verdicts = {
        name: a[key]
        .merge(var[var["variant"] == name], on=key, how="left", validate="1:1")["verdict"]
        .to_numpy()
        for name in VARIANTS
    }
    ca = a[key].merge(ca, on=key, how="left", validate="1:1")
    if radius != RADIUS:
        anchored15 = anchored15.assign(
            releasing_won=(anchored15["team_id_next"] == anchored15["team_id_i"]).astype(int)
        )
    else:
        anchored15 = base
    return {"base": base, "base15": anchored15, "a": a, "off": off, "variant_verdicts": variant_verdicts, "ca": ca,
            "drop15": drop15, "radius": radius, "names": names, "n_matches": n_matches, "clocks": clocks,
            "n_sets": len(matches)}  # fmt: skip


def _comparison(t: pd.DataFrame, a: str, b: str, n_matches: int) -> dict:
    def stat(d):
        return log_loss(d["releasing_won"], d[b]) - log_loss(d["releasing_won"], d[a])

    boot = np.array(bootstrap_within_match(t, stat, N_BOOT, SEED))
    lo, hi = np.quantile(boot, 0.025), np.quantile(boot, 0.975)
    same = int(sum(stat(d) > 0 for _, d in t.groupby("match_id")))
    return {
        "comparison": b,
        "log-loss p_dynamic": log_loss(t["releasing_won"], t[a]),
        "log-loss comparison": log_loss(t["releasing_won"], t[b]),
        "difference": stat(t),
        "lo": lo,
        "hi": hi,
        f"matches p_dynamic lower (of {n_matches})": same,
        "result": "pass" if (lo > 0 and same >= MATCHES_MIN) else "fail",
    }


def _verdict_shares(t: pd.DataFrame) -> pd.Series:
    return t["verdict"].value_counts(normalize=True).reindex(list(SHARES), fill_value=0.0)


def _by_trigger(t: pd.DataFrame, fn) -> pd.DataFrame:
    rows = [{"trigger": k, **fn(g)} for k, g in t.groupby("trigger")]
    rows.append({"trigger": "all", **fn(t)})
    return pd.DataFrame(rows)


def write(r: dict, out: Path) -> dict:
    """Write report.md and the MT1 files; return the gate summary."""
    out.mkdir(parents=True, exist_ok=True)
    base, base15, a, off = r["base"], r["base15"], r["a"], r["off"]
    names, n_matches, n_m, radius, drop15 = r["names"], r["n_matches"], r["n_sets"], r["radius"], r["drop15"]
    buf = io.StringIO()

    def say(*parts):
        print(*parts, file=buf)

    say(f"MT1 on the test matches ({n_m}): anchored main pairs {len(base15)}; camera-gate drop share at 15 m "
        f"{drop15:.4f}; radius of the main analysis {radius:.0f} m; analysis set {len(a)} lost balls\n")  # fmt: skip
    say("Gates V1 and V2 (difference: log-loss of the comparison minus log-loss of p_dynamic):\n")
    g12 = pd.DataFrame(
        [
            {"gate": "V1 against B0", **_comparison(a, "p_dynamic", "p_B0", n_m)},
            {"gate": "V1 against B1", **_comparison(a, "p_dynamic", "p_B1", n_m)},
            {"gate": "V2 against p_static", **_comparison(a, "p_dynamic", "p_static", n_m)},
        ]
    )
    say(md(g12))

    say("\nGate V3 (verdict unchanged under each variant on its own; base set fixed; frozen D5 parameter):\n")
    rows = []
    for name, verdicts in r["variant_verdicts"].items():
        same = (verdicts == a["verdict"].to_numpy()).mean()
        rows.append({"variant": name, "lost balls": len(a), "verdict unchanged": same,
                     "result": "pass" if same >= V3_MIN else "fail"})  # fmt: skip
    g3 = pd.DataFrame(rows)
    say(md(g3))

    rate = {w: (~base15.loc[base15["releasing_won"] == w, "kept"]).mean() for w in (1, 0)}
    gc = {"anchored pairs": len(base15), "dropped at 15 m": int((~base15["kept"]).sum()), "drop share at 15 m": drop15,
          "result": "pass" if drop15 <= GATE_MAX_DROP else "fail", "drop rate, releasing team won": rate[1],
          "drop rate, other team won": rate[0], "difference": rate[1] - rate[0]}  # fmt: skip
    say("\nCamera gate (D7, at most 30% of anchored main pairs dropped):\n")
    say(md(pd.DataFrame([gc])))

    v1 = bool((g12.loc[:1, "result"] == "pass").all())
    v2 = bool(g12.loc[2, "result"] == "pass")
    v3 = bool((g3["result"] == "pass").all())
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
    say("\nConsequences fixed in the brief:\n")
    say(md(consequences))

    say(
        f"\nR1. Categorical verdict shares of lost loose balls, pooled over teams (headline: {v1 and v2 and v3}):\n"
    )
    r1 = pd.DataFrame({"verdict": list(SHARES), "gated (D7 on)": _verdict_shares(a).to_numpy(),
                       "ungated (D7 off, extrapolated positions kept)": _verdict_shares(off).to_numpy()})  # fmt: skip
    say(md(pd.concat([r1, pd.DataFrame([{"verdict": "lost balls", "gated (D7 on)": len(a),
                                         "ungated (D7 off, extrapolated positions kept)": len(off)}])])))  # fmt: skip
    say("\nR2. Gated against ungated, by trigger (share of lost balls under each verdict):\n")
    rows = []
    for label, d in (("gated", a), ("ungated", off)):
        for k, g in d.groupby("trigger"):
            rows.append({"set": label, "trigger": k, "lost balls": len(g), **_verdict_shares(g).to_dict()})
    say(md(pd.DataFrame(rows), ".3f"))
    dropped = off[~off["kept"]]
    say(f"\nR2b. The {len(dropped)} lost balls that D7 drops, verdict shares:\n")
    say(md(pd.DataFrame([{"lost balls": len(dropped), **_verdict_shares(dropped).to_dict()}]), ".3f"))

    say("\nR3. Continuous deficit shares of the losing team, pooled and by trigger:\n")
    say(md(_by_trigger(a, lambda d: {"lost balls": len(d), **d[DEFICIT].mean().to_dict()}), ".3f"))

    say("\nR4. Calibration of p_dynamic, five bins:\n")
    say(md(calibration(a["p_dynamic"], a["releasing_won"]), ".3f"))

    base = base.assign(winner=np.where(base["releasing_won"] == 1, "releasing team", "other team"))
    say("\nR5. Immediate class (lead < 0.5 s), anchored main pairs, by trigger and by winner:\n")
    for by in ("trigger", "winner"):
        g = base.groupby(by)["immediate"].agg(episodes="size", immediate="sum", share="mean").reset_index()
        g = pd.concat([g, pd.DataFrame([{by: "all", "episodes": len(base), "immediate": int(base["immediate"].sum()),
                                         "share": base["immediate"].mean()}])])  # fmt: skip
        say(md(g, ".3f"))
        say()

    say("R6. D7 drop rates by trigger and by winner, and the releasing team's win-share difference:\n")
    say(md(_drop_rates(base, "trigger"), ".3f"))
    say()
    say(md(_drop_rates(base, "winner"), ".3f"))
    say()
    say(md(pd.DataFrame([_win_share_difference(base.reset_index(drop=True))]), ".3f"))

    say("\nR7. S2 reachability check by trigger (winner reach time <= lead + 0.3 s):\n")
    s2 = base.assign(within=base["t_winner"] <= base["lead_s"] + 0.3)
    for label, d in (("analysis set", s2[s2["kept"] & ~s2["immediate"]]), ("all anchored pairs", s2),
                     ("lead >= 0.5 s", s2[~s2["immediate"]])):  # fmt: skip
        say(f"{label}:\n")
        say(md(_by_trigger(d, lambda g: {"episodes": len(g), "share": g["within"].mean(),
                                         "winner not on anchor frame": int(g["t_winner"].isna().sum())}), ".3f"))  # fmt: skip
        say()

    say("R8. Constant-acceleration model (report-only):\n")
    ca = r["ca"]
    say(md(pd.DataFrame([{"log-loss DataBallPy p_dynamic": log_loss(a["releasing_won"], a["p_dynamic"]),
                          "log-loss constant-acceleration p_dynamic": log_loss(a["releasing_won"], ca["p_dynamic"]),
                          "verdicts that agree": (ca["verdict"].to_numpy() == a["verdict"].to_numpy()).mean()}])))  # fmt: skip

    flagged = {t for t, n in n_matches.items() if n <= 2}
    flagged |= {t for t, n in names.items() if t == NEWCASTLE or "Newcastle" in n}
    rep = team_report(a, N_BOOT, SEED, names, n_matches)
    tv = rep["verdicts"]
    tv = pd.concat(
        [pd.DataFrame({"team": tv["name"], "sample-size flag": ["flag" if t in flagged else "" for t in tv["team"]],
                       "matches in the set": tv["matches"], "lost": tv["lost"]}),
         tv[[c for v in SHARES for c in (v, f"{v} lo", f"{v} hi")]]],
        axis=1,
    )  # fmt: skip
    say(
        "\nR9a. Team-level categorical verdict shares over lost balls, 95% bootstrap intervals within match:\n"
    )
    say(md(tv, ".3f"))
    tc = rep["shares"]
    tc = pd.concat(
        [pd.DataFrame({"team": tc["team"], "name": tc["name"], "matches in the set": tc["matches"],
                       "sample-size flag": ["flag" if t in flagged else "" for t in tc["team"]],
                       "lost": tc["lost"], "won": tc["won"]}),
         tc[[c for k in ("deficit", "credit") for s in SHARES for c in (f"{k} {s}", f"{k} {s} lo", f"{k} {s} hi")]]],
        axis=1,
    )  # fmt: skip
    show = ["name", "matches in the set", "sample-size flag", "lost", "won"]
    show += [c for s in SHARES for c in (f"deficit {s}", f"deficit {s} lo", f"deficit {s} hi")]
    say(
        "\nR9b. Team-level continuous deficit shares over lost balls, 95% bootstrap intervals within match:\n"
    )
    say(md(tc[show], ".3f"))
    (out / "report.md").write_text(buf.getvalue())

    keep = ["match_id", "seq_i", "trigger", "anchor_frame", "pickup_frame", "lead_s", "releasing_won", "p_static",
            "p_dynamic", "p_B0", "p_B1", "losing_team", "winning_team", *DEFICIT, "verdict"]  # fmt: skip
    a[keep].assign(**{f"verdict {k}": v for k, v in r["variant_verdicts"].items()}).to_csv(
        out / "episodes.csv", index=False, float_format="%.4f"
    )
    off[keep + ["kept"]].to_csv(out / "episodes_ungated.csv", index=False, float_format="%.4f")
    tv.to_csv(out / "team_verdicts.csv", index=False, float_format="%.4f")
    tc.to_csv(out / "team_shares.csv", index=False, float_format="%.4f")
    export_clips(
        a[["match_id", "seq_i", "losing_team", "verdict"]],
        a[["match_id", "seq_i", "period_id", "anchor_frame"]],
        r["clocks"],
        path=out / "clips.csv",
    )
    summary = {"set": "test", "matches": n_m, "anchored pairs": len(base15), "analysis set": len(a), "radius": radius,
               "V1": v1, "V2": v2, "V3": v3, "camera gate": gc["result"] == "pass"}  # fmt: skip
    (out / "gates.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def _drop_rates(table: pd.DataFrame, by: str) -> pd.DataFrame:
    rows = [{by: v, "episodes": len(g), "dropped": int((~g["kept"]).sum()), "drop rate": (~g["kept"]).mean()}
            for v, g in table.groupby(by, sort=True)]  # fmt: skip
    rows.append({by: "all", "episodes": len(table), "dropped": int((~table["kept"]).sum()),
                 "drop rate": (~table["kept"]).mean()})  # fmt: skip
    return pd.DataFrame(rows)


def _win_share_difference(table: pd.DataFrame) -> dict:
    def diff(t):
        return t.loc[~t["kept"], "releasing_won"].mean() - t.loc[t["kept"], "releasing_won"].mean()

    boot = np.array(bootstrap_within_match(table, diff, N_BOOT, SEED))
    return {
        "win share dropped": table.loc[~table["kept"], "releasing_won"].mean(),
        "win share kept": table.loc[table["kept"], "releasing_won"].mean(),
        "difference": diff(table),
        "lo": np.nanquantile(boot, 0.025),
        "hi": np.nanquantile(boot, 0.975),
    }


def reproduce(data, out) -> dict:
    """Regenerate the MT1 tables and the README figures from the open-data clone at `data` into `out`."""
    from looseball.figures import draw_figures

    summary = write(compute(data), Path(out))
    figures = draw_figures(data, out)
    summary["figure 1 episode"] = (
        f"match {figures['figure 1']['match_id']}, seq_i {figures['figure 1']['seq_i']}"
    )
    summary["figure 1 seed"] = figures["figure 1"]["seed"]
    return summary
