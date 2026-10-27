"""A2 to A6 on the revised candidate set, T7 results, and audit/loose_episodes_exploration.csv.

Prints markdown tables for AUDIT.md. Gates are computed separately in scripts/gates.py.
"""

import numpy as np
import pandas as pd

from looseball import episodes, io, paths

TRIGGERS = list(episodes.LOOSE_TRIGGERS)


def md(t: pd.DataFrame, floatfmt: str = ".3f") -> str:
    return t.to_markdown(index=False, floatfmt=floatfmt)


def by_trigger(df: pd.DataFrame, fn) -> pd.DataFrame:
    """Apply fn to each trigger class and to the pooled set; one row each."""
    rows = [{"trigger": t, **fn(df[df["trigger"] == t])} for t in TRIGGERS if (df["trigger"] == t).any()]
    rows.append({"trigger": "all", **fn(df)})
    return pd.DataFrame(rows)


def q(s: pd.Series, probs=(0.1, 0.5, 0.9)) -> dict:
    s = s.dropna()
    return {f"p{round(p * 100)}": (np.quantile(s, p) if len(s) else np.nan) for p in probs}


def a2(main: pd.DataFrame) -> None:
    print(
        "A2a. Pickup point agreement: tracking ball on the pickup frame vs rotated event x_start, y_start of i+1:\n"
    )

    def f(d):
        dist = d["pickup_disagreement_m"]
        ok = dist.dropna()
        return {
            "pairs": len(d),
            "no pickup point": int(dist.isna().sum()),
            **{f"{k} m": v for k, v in q(dist, (0.1, 0.5, 0.9, 0.95)).items()},
            "share <= 2 m": (ok <= 2).mean(),
            "share <= 5 m": (ok <= 5).mean(),
        }

    print(md(by_trigger(main, f)))
    print("\nA2b. Same, by frame class of the pickup frame:\n")
    rows = [
        {"pickup frame class": c, **f(main[main["pickup_frame_class"] == c])}
        for c in ("camera", "no_camera", "empty")
    ]
    print(md(pd.DataFrame(rows)))
    print("\nA2c. Rotation check, all main pairs with a pickup point:\n")
    ok = main[main["pickup_disagreement_m"].notna()]
    rows = []
    for label, col in (
        ("(x, y) to (-x, -y) when right_to_left (used)", "pickup_disagreement_m"),
        ("x only mirrored when right_to_left", "pickup_disagreement_xmirror_m"),
        ("no rotation", "pickup_disagreement_norotation_m"),
    ):
        rows.append(
            {
                "event frame to tracking frame": label,
                "median m": ok[col].median(),
                "share <= 2 m": (ok[col] <= 2).mean(),
                "share <= 5 m": (ok[col] <= 5).mean(),
            }
        )
    print(md(pd.DataFrame(rows)))


def a3(main: pd.DataFrame) -> None:
    print("\nA3. Ball visibility in the window, main pairs:\n")

    def f(d):
        return {
            "pairs": len(d),
            "window frames": int(d["window_frames"].sum()),
            "share of window frames ball detected": d["window_ball_detected"].sum()
            / d["window_frames"].sum(),
            "share of pairs with a no-camera or empty window frame": d["window_camera_loss"].mean(),
            "with a no-camera frame": (d["window_no_camera"] > 0).mean(),
            "with an empty frame": (d["window_empty"] > 0).mean(),
            "share release or pickup frame not camera": (
                (d["release_frame_class"] != "camera") | (d["pickup_frame_class"] != "camera")
            ).mean(),
        }

    print(md(by_trigger(main, f)))


def a4(main: pd.DataFrame) -> None:
    has_point = main[main["pickup_x"].notna()]
    print(
        f"\nA4a. Players within radius of the pickup point, main pairs with a pickup point "
        f"({len(has_point)} of {len(main)}). Mean count per pair by team; detected shares pooled over players:\n"
    )
    rows = []
    for frame in ("release", "pickup"):
        for radius in episodes.RADII:

            def f(d, frame=frame, radius=radius):
                n_rel = d[f"{frame}_n{radius}_releasing"]
                n_oth = d[f"{frame}_n{radius}_other"]
                k_rel = d[f"{frame}_det{radius}_releasing"]
                k_oth = d[f"{frame}_det{radius}_other"]
                return {
                    "frame": frame,
                    "radius m": radius,
                    "pairs": len(d),
                    "mean n releasing team": n_rel.mean(),
                    "mean n other team": n_oth.mean(),
                    "detected share releasing": k_rel.sum() / n_rel.sum(),
                    "detected share other": k_oth.sum() / n_oth.sum(),
                    "detected share all": (k_rel.sum() + k_oth.sum()) / (n_rel.sum() + n_oth.sum()),
                }

            rows.append(by_trigger(has_point, f))
    t = pd.concat(rows, ignore_index=True)
    t = t[
        ["frame", "radius m", "trigger", *[c for c in t.columns if c not in ("frame", "radius m", "trigger")]]
    ]
    print(md(t, ".2f"))
    print(
        "\nA4b. Winner detected on the pickup frame and fully_extrapolated of possession i+1, all main pairs:\n"
    )

    def g(d):
        return {
            "pairs": len(d),
            "winner detected on pickup frame": d["winner_detected_pickup"].mean(),
            "i+1 fully_extrapolated TRUE": d["fully_extrapolated_next"].eq(True).mean(),
        }

    print(md(by_trigger(main, g)))


def a5(ep: pd.DataFrame, p_all: pd.DataFrame) -> None:
    main = ep[ep["main"]]
    print("\nA5a. Exclusion flow, all five matches (each row applies its rule to the row above):\n")
    r = p_all[p_all["retained"]]
    steps = [("retained pairs", r)]
    steps.append(("trigger T1 to T7", steps[-1][1][steps[-1][1]["trigger"].isin(episodes.LOOSE_TRIGGERS)]))
    s = steps[-1][1]
    steps.append(
        ("resolution recovery or keep_possession", s[s["resolution"].isin(episodes.CANDIDATE_RESOLUTIONS)])
    )
    s = steps[-1][1]
    steps.append(("not a T3 pair won by GK", s[~s["gk_save"]]))
    s = steps[-1][1]
    steps.append(("not the same player", s[s["continuity"] != "same player"]))
    s = steps[-1][1]
    steps.append(("gap >= 1 frame (candidate pairs, G2 set)", s[s["gap"] >= 1]))
    s = steps[-1][1]
    steps.append(("gap >= 3 frames (main pairs)", s[s["gap"] >= episodes.MIN_GAP]))
    print(md(pd.DataFrame([{"step": k, "pairs": len(v)} for k, v in steps])))

    print("\nA5b. Volume per match:\n")
    sc = main.drop_duplicates(["match_id", "scramble_id"])
    vol = pd.DataFrame(
        {
            "candidate pairs (gap >= 1)": ep.groupby("match_id").size(),
            "main pairs (gap >= 3)": main.groupby("match_id").size(),
            "merged scrambles": sc.groupby("match_id").size(),
        }
    )
    vol.loc["total"] = vol.sum()
    print(md(vol.reset_index().rename(columns={"index": "match_id"}), ".0f"))

    print("\nA5c. Main pairs per match by trigger class:\n")
    ct = pd.crosstab(
        main["match_id"], pd.Categorical(main["trigger"], TRIGGERS), margins=True, margins_name="total"
    )
    print(ct.reset_index().rename(columns={"row_0": "match_id"}).to_markdown(index=False))

    first = main[main["scramble_link"] == 1].set_index(["match_id", "scramble_id"])["trigger"]
    aerial_any = main.groupby(["match_id", "scramble_id"])["aerial"].any()
    sct = pd.DataFrame({"trigger": first, "aerial": aerial_any}).reset_index()
    print("\nA5d. Merged scrambles per match by trigger class of the first link:\n")
    ct = pd.crosstab(
        sct["match_id"], pd.Categorical(sct["trigger"], TRIGGERS), margins=True, margins_name="total"
    )
    print(ct.reset_index().rename(columns={"row_0": "match_id"}).to_markdown(index=False))

    print("\nA5e. Aerial or ground per match, main pairs and merged scrambles:\n")
    ag = pd.DataFrame(
        {
            "main pairs aerial": main.groupby("match_id")["aerial"].sum(),
            "main pairs ground": main.groupby("match_id")["aerial"].apply(lambda s: (~s).sum()),
            "scrambles aerial": sct.groupby("match_id")["aerial"].sum(),
            "scrambles ground": sct.groupby("match_id")["aerial"].apply(lambda s: (~s).sum()),
        }
    ).astype(int)
    ag.loc["total"] = ag.sum()
    print(ag.reset_index().rename(columns={"index": "match_id"}).to_markdown(index=False))

    print("\nA5f. Scramble size (links = main pairs merged):\n")
    links = sc["scramble_links"].clip(upper=4).map({1: "1", 2: "2", 3: "3", 4: "4 or more"})
    print(md(links.value_counts().sort_index().rename_axis("links").rename("scrambles").reset_index(), ".0f"))

    print("\nA5g. Phases of play (team_in_possession_phase_type) and main pairs by release frame:\n")
    rows = []
    for m in paths.EXPLORATION:
        ph = io.load_phases(m).sort_values("frame_start").reset_index(drop=True)
        rel = main.loc[main["match_id"] == m, "release_frame"].to_numpy()
        k = np.searchsorted(ph["frame_end"].to_numpy(), rel, side="left")
        inside = (k < len(ph)) & (ph["frame_start"].to_numpy()[np.minimum(k, len(ph) - 1)] <= rel)
        kind = np.where(
            inside, ph["team_in_possession_phase_type"].to_numpy()[np.minimum(k, len(ph) - 1)], "no phase"
        )
        hit = set(k[inside])
        for i, typ in enumerate(ph["team_in_possession_phase_type"]):
            rows.append({"kind": "phase", "type": typ, "has_episode": i in hit})
        for typ in kind:
            rows.append({"kind": "episode", "type": typ})
    t = pd.DataFrame(rows)
    phases = t[t["kind"] == "phase"].groupby("type")["has_episode"].agg(phases="size", with_episode="sum")
    eps = t[t["kind"] == "episode"].groupby("type").size().rename("main pairs released in it")
    out = phases.join(eps, how="outer").fillna(0)
    out["share of phases with an episode"] = out["with_episode"] / out["phases"]
    out["share of main pairs"] = out["main pairs released in it"] / len(main)
    out = out.reset_index().rename(columns={"with_episode": "phases with an episode"})
    print(md(out, ".3f"))

    print("\nA5h. Winner counts by match and team (plain counts; no predictor is related to them):\n")
    names = {}
    for m in paths.EXPLORATION:
        meta = io.load_metadata(m)
        for side in ("home_team", "away_team"):
            names[(m, meta[side]["id"])] = meta[side]["short_name"]
    w_pairs = main.groupby(["match_id", "team_id_next"]).size().rename("main pairs won")
    w_sc = sc.groupby(["match_id", "scramble_winner_team"]).size().rename("scrambles won")
    w_sc.index.names = ["match_id", "team_id_next"]
    w = pd.concat([w_pairs, w_sc], axis=1).fillna(0).astype(int).reset_index()
    w.insert(2, "team", [names[(m, t)] for m, t in zip(w["match_id"], w["team_id_next"])])
    print(w.rename(columns={"team_id_next": "team_id"}).to_markdown(index=False))


def a6(main: pd.DataFrame) -> None:
    print("\nA6a. Flight geometry, main pairs (quantiles p10, p50, p90):\n")

    def f(d):
        z = d["max_ball_z_detected"]
        return {
            "pairs": len(d),
            **{f"window s {k}": v for k, v in q(d["gap"] / paths.FPS).items()},
            "pairs with a detected window frame": int(z.notna().sum()),
            **{f"max z m {k}": v for k, v in q(z).items()},
            "share aerial": d["aerial"].mean(),
            "pairs with ball at both ends": int(d["ball_displacement_m"].notna().sum()),
            **{f"ball distance m {k}": v for k, v in q(d["ball_displacement_m"]).items()},
        }

    print(md(by_trigger(main, f), ".2f"))
    print("\nA6b. Gap tail, main pairs (seconds):\n")

    def g(d):
        s = d["gap"] / paths.FPS
        return {
            "pairs": len(d),
            **{f"{k} s": v for k, v in q(s, (0.9, 0.95, 0.99)).items()},
            "max s": s.max(),
            "gap > 5 s": int((s > 5).sum()),
            "gap > 10 s": int((s > 10).sum()),
        }

    print(md(by_trigger(main, g), ".2f"))


def t7(ep: pd.DataFrame) -> None:
    d = ep[ep["trigger"] == "T7"]
    print("\nT7a. T7 candidate pairs (gap >= 1), gap quantiles (seconds) by resolution and continuity:\n")
    rows = []
    for (res, cont), g in d.groupby(["resolution", "continuity"]):
        s = g["gap"] / paths.FPS
        rows.append(
            {
                "resolution": res,
                "continuity": cont,
                "pairs": len(g),
                **q(s),
                "share gap >= 3 fr": (g["gap"] >= 3).mean(),
            }
        )
    s = d["gap"] / paths.FPS
    rows.append(
        {
            "resolution": "all",
            "continuity": "all",
            "pairs": len(d),
            **q(s),
            "share gap >= 3 fr": (d["gap"] >= 3).mean(),
        }
    )
    print(md(pd.DataFrame(rows), ".2f"))
    print("\nT7b. T7 candidate pairs, gap in frames by bucket:\n")
    buckets = pd.cut(
        d["gap"],
        [0, 2, 5, 10, 20, 30, 50, np.inf],
        labels=["1-2", "3-5", "6-10", "11-20", "21-30", "31-50", ">50"],
    )
    print(
        md(buckets.value_counts().sort_index().rename_axis("gap frames").rename("pairs").reset_index(), ".0f")
    )


CSV_COLUMNS = [
    "match_id", "seq_i", "seq_next", "event_id_i", "event_id_next", "index_i", "index_next",
    "trigger", "resolution", "continuity", "gap", "main", "aerial", "max_ball_z_detected",
    "scramble_id", "scramble_link", "scramble_links", "release_frame", "pickup_frame",
    "release_frame_class", "pickup_frame_class", "pickup_x", "pickup_y", "pickup_event_x", "pickup_event_y",
    "pickup_disagreement_m", "window_frames", "window_ball_detected", "ball_detected_share",
    "window_no_camera", "window_empty", "ball_displacement_m",
    *[f"{fr}_{k}{r}_{s}" for fr in ("release", "pickup") for r in episodes.RADII for k in ("n", "det") for s in ("releasing", "other")],
    "winner_detected_pickup", "fully_extrapolated_next", "team_id_i", "team_id_next", "player_id_next",
]  # fmt: skip


def main() -> None:
    p_all = episodes.all_pairs()
    ep = episodes.all_episodes()
    ep["ball_detected_share"] = ep["window_ball_detected"] / ep["window_frames"]
    main_set = ep[ep["main"]]
    a2(main_set)
    a3(main_set)
    a4(main_set)
    a5(ep, p_all)
    a6(main_set)
    t7(ep)
    out = paths.AUDIT_DIR / "loose_episodes_exploration.csv"
    ep = ep.astype({c: "Int64" for c in ("scramble_id", "scramble_link", "scramble_links")})
    ep[CSV_COLUMNS].rename(
        columns={"team_id_next": "winner_team_id", "player_id_next": "winner_player_id"}
    ).to_csv(out, index=False, float_format="%.3f")
    print(f"\ncsv: {out.relative_to(paths.ROOT)} ({len(ep)} rows)")


if __name__ == "__main__":
    main()
