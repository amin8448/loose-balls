"""A7 (anchors and leads), A8 (contacts) and A9 (extrapolation plausibility) on the main pairs.

Prints markdown tables for AUDIT.md. Definitions: revision 2 amended in AUDIT.md.
"""

import numpy as np
import pandas as pd

from looseball import episodes, paths, tracking

TRIGGERS = list(episodes.LOOSE_TRIGGERS)
SPRINT = 9.0  # m/s


def md(t: pd.DataFrame, floatfmt: str = ".3f") -> str:
    return t.to_markdown(index=False, floatfmt=floatfmt)


def q(s: pd.Series, probs=(0.1, 0.5, 0.9)) -> dict:
    s = s.dropna()
    return {f"p{round(p * 100)}": (np.quantile(s, p) if len(s) else np.nan) for p in probs}


def grouped(df: pd.DataFrame, key: str, levels: list, fn) -> pd.DataFrame:
    rows = [{key: v, **fn(df[df[key] == v])} for v in levels if (df[key] == v).any()]
    rows.append({key: "all", **fn(df)})
    return pd.DataFrame(rows)


def a7(main: pd.DataFrame) -> None:
    for leg, label in (("1", "first leg"), ("2", "last leg")):

        def f(d, leg=leg):
            anchor, start, lead = d[f"anchor{leg}_frame"], d[f"leg{leg}_start"], d[f"lead{leg}_s"]
            has = anchor.notna()
            return {
                "pairs": len(d),
                "anchor at leg start": (anchor == start).mean(),
                "no anchor": (~has).mean(),
                **{f"lead s {k}": v for k, v in q(lead).items()},
                "lead < 0.5 s (of anchored)": (lead[has] < 0.5).mean() if has.any() else np.nan,
            }

        print(f"\nA7a ({label}). Anchors and leads by trigger class:\n")
        print(md(grouped(main, "trigger", TRIGGERS, f)))
        print(f"\nA7b ({label}). Anchors and leads, aerial or ground:\n")
        print(
            md(
                grouped(
                    main.assign(flight=np.where(main["aerial"], "aerial", "ground")),
                    "flight",
                    ["aerial", "ground"],
                    f,
                )
            )
        )

    print("\nA7c. Aerial pairs: apex (largest detected ball_data.z) relative to pickup:\n")

    def g(d):
        obs = d["apex_observed"]
        return {
            "aerial pairs": len(d),
            "apex unobserved": (~obs).mean(),
            **{f"apex before pickup s {k}": v for k, v in q(d.loc[obs, "apex_to_pickup_s"]).items()},
        }

    print(md(grouped(main[main["aerial"]], "trigger", TRIGGERS, g)))


def a8(main: pd.DataFrame) -> None:
    print("\nA8a. Contacts per pair by trigger class, and the share of testable window time:\n")

    def f(d):
        n = d["n_contacts"]
        return {
            "pairs": len(d),
            "0 contacts": (n == 0).mean(),
            "1": (n == 1).mean(),
            "2": (n == 2).mean(),
            "3 or more": (n >= 3).mean(),
            "uncovered share of window time": 1
            - d["contact_evaluable_frames"].sum() / d["contact_domain_frames"].sum(),
        }

    print(md(grouped(main, "trigger", TRIGGERS, f)))
    print(
        "\nA8b. Release to first contact (pairs with a contact) and duration of the last leg (all pairs), seconds:\n"
    )

    def g(d):
        first = (d["leg1_end"] - d["leg1_start"]) / paths.FPS
        last = (d["leg2_end"] - d["leg2_start"]) / paths.FPS
        has = d["n_contacts"] > 0
        return {
            "pairs": len(d),
            "with a contact": int(has.sum()),
            **{f"to first contact {k}": v for k, v in q(first[has]).items()},
            **{f"last leg {k}": v for k, v in q(last).items()},
        }

    print(md(grouped(main, "trigger", TRIGGERS, g), ".2f"))
    print("\nA8c. Ball path length next to the straight-line distance of A6, metres:\n")

    def h(d):
        ratio = d["path_length_m"] / d["ball_displacement_m"]
        return {
            "pairs": len(d),
            "path p50": d["path_length_m"].median(),
            "straight p50": d["ball_displacement_m"].median(),
            **{f"path / straight {k}": v for k, v in q(ratio).items()},
            "pairs with a skipped step": int((d["path_missing_segments"] > 0).sum()),
        }

    print(md(grouped(main, "trigger", TRIGGERS, h), ".2f"))
    print("\nA8d. Legs per pair:\n")
    print(
        md(
            main["n_legs"]
            .clip(upper=4)
            .value_counts()
            .sort_index()
            .rename_axis("legs (4 = 4 or more)")
            .rename("pairs")
            .reset_index(),
            ".0f",
        )
    )


def a8_positions(main: pd.DataFrame) -> None:
    """Where contacts sit relative to release and pickup, and who is within 1.5 m (diagnostic)."""
    rows = []
    for m, d in main[main["n_contacts"] > 0].groupby("match_id"):
        fr = tracking.load_frames(m)
        pl = tracking.load_players(m).set_index(["frame", "player_id"])[["x", "y"]]
        for r in d.itertuples(index=False):
            frames = [int(f) for f in r.contact_frames.split(";")]
            for k, f in enumerate(frames):
                ball = fr.loc[f, ["ball_data.x", "ball_data.y"]].to_numpy(dtype=float)

                def within(pid, f=f, ball=ball, pl=pl):
                    if (f, pid) not in pl.index:
                        return False
                    return bool(
                        np.hypot(*(pl.loc[(f, pid)].to_numpy(dtype=float) - ball))
                        <= episodes.CONTACT_PLAYER_RADIUS
                    )

                rows.append(
                    {
                        "first": k == 0,
                        "last": k == len(frames) - 1,
                        "after release": f - r.release_frame,
                        "before pickup": r.pickup_frame - f,
                        "releasing player within 1.5 m": within(r.player_id_i),
                        "winner within 1.5 m": within(r.player_id_next),
                    }
                )
    c = pd.DataFrame(rows)
    bins, labels = [0, 1, 2, 5, np.inf], ["1", "2", "3-5", "6 or more"]
    print(
        "\nA8e (diagnostic). First contacts by frames after release, and last contacts by frames before pickup:\n"
    )
    out = []
    for which, col, who in (
        ("first contact", "after release", "releasing player within 1.5 m"),
        ("last contact", "before pickup", "winner within 1.5 m"),
    ):
        d = c[c[which.split()[0]]]
        b = pd.cut(d[col], bins, labels=labels)
        for lab in labels:
            g = d[b == lab]
            out.append(
                {
                    "contact": which,
                    "frames from the window edge": f"{lab} {col}",
                    "contacts": len(g),
                    "player checked": who.replace(" within 1.5 m", ""),
                    "share with that player within 1.5 m": g[who].mean() if len(g) else np.nan,
                }
            )
    print(md(pd.DataFrame(out)))


def a8_runs(main: pd.DataFrame) -> None:
    """Contacts on consecutive frames grouped into runs (diagnostic; the rule itself is unchanged)."""

    def runs(s: str) -> int:
        f = np.array([int(x) for x in s.split(";")]) if s else np.array([], dtype=int)
        return int(len(f) and 1 + (np.diff(f) > 1).sum())

    n_runs = main["contact_frames"].map(runs)
    print("\nA8f (diagnostic). Contacts and runs of consecutive contact frames, by trigger class:\n")

    def f(d):
        r = n_runs[d.index]
        return {
            "pairs": len(d),
            "contacts": int(d["n_contacts"].sum()),
            "runs": int(r.sum()),
            "contacts per run": d["n_contacts"].sum() / r.sum() if r.sum() else np.nan,
            "0 runs": (r == 0).mean(),
            "1 run": (r == 1).mean(),
            "2 runs": (r == 2).mean(),
            "3 or more runs": (r >= 3).mean(),
        }

    print(md(grouped(main, "trigger", TRIGGERS, f)))


def a9(main: pd.DataFrame, chk: pd.DataFrame) -> None:
    print("\nA9. Players within 15 m of the pickup point at the last-leg anchor, not detected at release:\n")
    anchored = main[main["anchor2_frame"].notna()]

    def f(trig):
        d = chk if trig == "all" else chk[chk["trigger"] == trig]
        a = anchored if trig == "all" else anchored[anchored["trigger"] == trig]
        meas = d[d["status"] == "measured"]
        return {
            "trigger": trig,
            "players within 15 m at anchor": int(a["anchor2_n15"].sum()),
            "not detected at release": len(d),
            "absent at release": int((d["status"] == "absent at release").sum()),
            "not detected by pickup": int((d["status"] == "not detected by the pickup frame").sum()),
            "measured": len(meas),
            **{
                f"speed m/s {k}": v
                for k, v in q(meas["speed"] if len(meas) else pd.Series(dtype=float)).items()
            },
            "max m/s": meas["speed"].max() if len(meas) else np.nan,
            "seconds to first detection p50": meas["seconds"].median() if len(meas) else np.nan,
            "share above 9 m/s": (meas["speed"] > SPRINT).mean() if len(meas) else np.nan,
        }

    print(
        md(
            pd.DataFrame(
                [f(t) for t in [*TRIGGERS, "all"] if t == "all" or (anchored["trigger"] == t).any()]
            ),
            ".2f",
        )
    )


def main() -> None:
    ep = episodes.all_episodes()
    main_set = ep[ep["main"]]
    a7(main_set)
    a8(main_set)
    a8_positions(main_set)
    a8_runs(main_set)
    a9(main_set, episodes.all_extrapolation_checks())


if __name__ == "__main__":
    main()
