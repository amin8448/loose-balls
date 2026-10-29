"""Gates after revision 2 amended: G1 and G3 re-run, G4 at the first-leg and last-leg anchors.

Thresholds and procedure as logged in AUDIT.md before this script was run.
"""

import pandas as pd
from gates import (
    G1_MIN_SCRAMBLES,
    G3_MAX_CAMERA_LOSS,
    G3_MIN_DETECTED,
    G4_MIN_PLAYERS_DETECTED,
    G4_MIN_WINNER_DETECTED,
    g3_values,
    verdict,
)

from looseball_research import episodes

EPISODE_SHARE = 0.85  # per-episode detected share counted as observed (reported, no threshold)


def pooled(d: pd.DataFrame, n_cols: list[str], k_cols: list[str]) -> float:
    return d[k_cols].to_numpy().sum() / d[n_cols].to_numpy().sum()


def episode_level(d: pd.DataFrame, n_cols: list[str], k_cols: list[str]) -> float:
    n, k = d[n_cols].sum(axis=1), d[k_cols].sum(axis=1)
    return ((n == 0) | (k >= EPISODE_SHARE * n)).mean()


def g4_at(d: pd.DataFrame, leg: str, radius: int) -> dict:
    a_n, a_k = [f"anchor{leg}_n{radius}"], [f"anchor{leg}_det{radius}"]
    p_n = [f"pickup_n{radius}_releasing", f"pickup_n{radius}_other"]
    p_k = [f"pickup_det{radius}_releasing", f"pickup_det{radius}_other"]
    return {
        "anchor pooled": pooled(d, a_n, a_k),
        "anchor episode level": episode_level(d, a_n, a_k),
        "pickup pooled": pooled(d, p_n, p_k),
        "pickup episode level": episode_level(d, p_n, p_k),
        "winner": d["winner_detected_pickup"].mean(),
    }


def passes(v: dict) -> bool:
    return (
        v["anchor pooled"] >= G4_MIN_PLAYERS_DETECTED
        and v["pickup pooled"] >= G4_MIN_PLAYERS_DETECTED
        and v["winner"] >= G4_MIN_WINNER_DETECTED
    )


def main() -> None:
    ep = episodes.all_episodes()
    main_set = ep[ep["main"]]
    rows = []

    sc = main_set.drop_duplicates(["match_id", "scramble_id"]).groupby("match_id").size()
    rows.append(
        (
            "G1",
            "merged scrambles, minimum over matches",
            f"{sc.min()} (match {sc.idxmin()})",
            f">= {G1_MIN_SCRAMBLES}",
            verdict(bool((sc >= G1_MIN_SCRAMBLES).all())),
        )
    )
    det, loss = g3_values(main_set)
    rows.append(
        (
            "G3",
            f"ball detected, share of window frames (n = {len(main_set)})",
            f"{det:.3f}",
            f">= {G3_MIN_DETECTED:.2f}",
            verdict(det >= G3_MIN_DETECTED),
        )
    )
    rows.append(
        (
            "G3",
            "pairs with a no-camera or empty window frame",
            f"{loss:.3f}",
            f"<= {G3_MAX_CAMERA_LOSS:.2f}",
            verdict(loss <= G3_MAX_CAMERA_LOSS),
        )
    )

    results = {}
    for leg, name in (("1", "first-leg anchor"), ("2", "last-leg anchor")):
        d = main_set[main_set[f"anchor{leg}_frame"].notna()]
        lost = 1 - len(d) / len(main_set)
        v = g4_at(d, leg, 15)
        ok = passes(v)
        tag = f"G4 {name}"
        rows.append(
            (
                tag,
                f"pairs with an anchor (lost to the camera: {lost:.3f})",
                f"{len(d)} of {len(main_set)}",
                "",
                "",
            )
        )
        rows.append(
            (
                tag,
                "players within 15 m detected at the anchor, pooled",
                f"{v['anchor pooled']:.4f}",
                f">= {G4_MIN_PLAYERS_DETECTED:.2f}",
                verdict(v["anchor pooled"] >= G4_MIN_PLAYERS_DETECTED),
            )
        )
        rows.append((tag, "same, episode level (reported)", f"{v['anchor episode level']:.4f}", "none", ""))
        rows.append(
            (
                tag,
                "players within 15 m detected at pickup, pooled",
                f"{v['pickup pooled']:.4f}",
                f">= {G4_MIN_PLAYERS_DETECTED:.2f}",
                verdict(v["pickup pooled"] >= G4_MIN_PLAYERS_DETECTED),
            )
        )
        rows.append((tag, "same, episode level (reported)", f"{v['pickup episode level']:.4f}", "none", ""))
        rows.append(
            (
                tag,
                "winner detected on the pickup frame",
                f"{v['winner']:.4f}",
                f">= {G4_MIN_WINNER_DETECTED:.2f}",
                verdict(v["winner"] >= G4_MIN_WINNER_DETECTED),
            )
        )
        if not ok:
            v10 = g4_at(d, leg, 10)
            ok = passes(v10)
            rows.append(
                (
                    f"{tag} recheck",
                    "10 m: anchor pooled / pickup pooled / winner",
                    f"{v10['anchor pooled']:.4f} / {v10['pickup pooled']:.4f} / {v10['winner']:.4f}",
                    "same",
                    verdict(ok),
                )
            )
            rows.append(
                (
                    f"{tag} recheck",
                    "10 m: anchor / pickup episode level (reported)",
                    f"{v10['anchor episode level']:.4f} / {v10['pickup episode level']:.4f}",
                    "none",
                    "",
                )
            )
        rows.append((tag, "verdict", "", "", verdict(ok)))
        results[name] = ok

    print("Gate verdicts at the anchors, contact rule of revision 3:\n")
    print(
        pd.DataFrame(rows, columns=["gate", "criterion", "value", "threshold", "result"]).to_markdown(
            index=False
        )
    )

    for leg, name in (("1", "first-leg anchor"), ("2", "last-leg anchor")):
        print(
            f"\nG4 at the {name} by trigger class (15 m; lost share over all main pairs, the rest over pairs with an anchor):\n"
        )
        t = []
        for trig in [*episodes.LOOSE_TRIGGERS, "all"]:
            all_t = main_set if trig == "all" else main_set[main_set["trigger"] == trig]
            if not len(all_t):
                continue
            d = all_t[all_t[f"anchor{leg}_frame"].notna()]
            v = g4_at(d, leg, 15) if len(d) else {}
            t.append(
                {"trigger": trig, "pairs": len(all_t), "lost to the camera": 1 - len(d) / len(all_t), **v}
            )
        print(pd.DataFrame(t).to_markdown(index=False, floatfmt=".3f"))

    either = any(results.values())
    print(f"\nG4 passes at either anchor: {either}")


if __name__ == "__main__":
    main()
