"""G1 to G4 with the thresholds and recheck rules logged in AUDIT.md before this script was run."""

import numpy as np
import pandas as pd

from looseball import episodes, paths

G1_MIN_SCRAMBLES = 50
G2_MIN_MEDIAN_FRAMES = 5
G2_MIN_SHARE_GE3 = 0.60
G3_MIN_DETECTED = 0.85
G3_MAX_CAMERA_LOSS = 0.25
G3_MARGIN = 0.05
G3_RECHECK_MAX_GAP = 20
G4_MIN_PLAYERS_DETECTED = 0.85
G4_MIN_WINNER_DETECTED = 0.90


def verdict(ok: bool) -> str:
    return "pass" if ok else "fail"


def g3_values(d: pd.DataFrame) -> tuple[float, float]:
    return d["window_ball_detected"].sum() / d["window_frames"].sum(), d["window_camera_loss"].mean()


def g4_values(d: pd.DataFrame, radius: int) -> tuple[float, float, float]:
    has_point = d[d["pickup_x"].notna()]
    shares = []
    for frame in ("release", "pickup"):
        n = has_point[[f"{frame}_n{radius}_releasing", f"{frame}_n{radius}_other"]].to_numpy().sum()
        k = has_point[[f"{frame}_det{radius}_releasing", f"{frame}_det{radius}_other"]].to_numpy().sum()
        shares.append(k / n)
    return shares[0], shares[1], d["winner_detected_pickup"].mean()


def main() -> None:
    ep = episodes.all_episodes()
    main_set = ep[ep["main"]]
    rows = []

    sc = main_set.drop_duplicates(["match_id", "scramble_id"]).groupby("match_id").size()
    g1_ok = bool((sc >= G1_MIN_SCRAMBLES).all())
    print("G1 per match (merged scrambles of main pairs):\n")
    print(sc.rename("merged scrambles").reset_index().to_markdown(index=False))
    rows.append(
        (
            "G1",
            "merged scrambles, minimum over matches",
            f"{sc.min()} (match {sc.idxmin()})",
            f">= {G1_MIN_SCRAMBLES}",
            verdict(g1_ok),
        )
    )

    gap = ep["gap"]
    med, share3 = float(np.median(gap)), float((gap >= 3).mean())
    g2_ok = med >= G2_MIN_MEDIAN_FRAMES and share3 >= G2_MIN_SHARE_GE3
    rows.append(
        (
            "G2",
            f"median gap, candidate pairs gap >= 1 (n = {len(ep)})",
            f"{med:.1f} frames ({med / paths.FPS:.2f} s)",
            f">= {G2_MIN_MEDIAN_FRAMES} frames",
            verdict(med >= G2_MIN_MEDIAN_FRAMES),
        )
    )
    rows.append(
        (
            "G2",
            "share with gap >= 3 frames",
            f"{share3:.3f}",
            f">= {G2_MIN_SHARE_GE3:.2f}",
            verdict(share3 >= G2_MIN_SHARE_GE3),
        )
    )
    rows.append(("G2", "verdict", "", "", verdict(g2_ok)))

    det, loss = g3_values(main_set)
    det_ok, loss_ok = det >= G3_MIN_DETECTED, loss <= G3_MAX_CAMERA_LOSS
    rows.append(
        (
            "G3",
            f"ball detected, share of window frames, main pairs (n = {len(main_set)})",
            f"{det:.3f}",
            f">= {G3_MIN_DETECTED:.2f}",
            verdict(det_ok),
        )
    )
    rows.append(
        (
            "G3",
            "pairs with a no-camera or empty window frame",
            f"{loss:.3f}",
            f"<= {G3_MAX_CAMERA_LOSS:.2f}",
            verdict(loss_ok),
        )
    )
    g3_ok = det_ok and loss_ok
    if not g3_ok:
        small = (det_ok or det >= G3_MIN_DETECTED - G3_MARGIN) and (
            loss_ok or loss <= G3_MAX_CAMERA_LOSS + G3_MARGIN
        )
        if small:
            short = main_set[main_set["gap"] <= G3_RECHECK_MAX_GAP]
            det2, loss2 = g3_values(short)
            g3_ok = det2 >= G3_MIN_DETECTED and loss2 <= G3_MAX_CAMERA_LOSS
            rows.append(
                (
                    "G3 recheck",
                    f"windows <= 2 s (n = {len(short)}): detected / camera loss",
                    f"{det2:.3f} / {loss2:.3f}",
                    "same",
                    verdict(g3_ok),
                )
            )
        else:
            rows.append(("G3", "miss larger than 5 points: no recheck", "", "", "fail"))
    rows.append(("G3", "verdict", "", "", verdict(g3_ok)))

    rel15, pk15, win = g4_values(main_set, 15)
    g4_ok = (
        rel15 >= G4_MIN_PLAYERS_DETECTED and pk15 >= G4_MIN_PLAYERS_DETECTED and win >= G4_MIN_WINNER_DETECTED
    )
    rows.append(
        (
            "G4",
            f"players within 15 m detected, release frame (n = {len(main_set)})",
            f"{rel15:.4f}",
            f">= {G4_MIN_PLAYERS_DETECTED:.2f}",
            verdict(rel15 >= G4_MIN_PLAYERS_DETECTED),
        )
    )
    rows.append(
        (
            "G4",
            "players within 15 m detected, pickup frame",
            f"{pk15:.4f}",
            f">= {G4_MIN_PLAYERS_DETECTED:.2f}",
            verdict(pk15 >= G4_MIN_PLAYERS_DETECTED),
        )
    )
    rows.append(
        (
            "G4",
            "winner detected on pickup frame",
            f"{win:.4f}",
            f">= {G4_MIN_WINNER_DETECTED:.2f}",
            verdict(win >= G4_MIN_WINNER_DETECTED),
        )
    )
    if not g4_ok:
        rel10, pk10, _ = g4_values(main_set, 10)
        g4_ok = (
            rel10 >= G4_MIN_PLAYERS_DETECTED
            and pk10 >= G4_MIN_PLAYERS_DETECTED
            and win >= G4_MIN_WINNER_DETECTED
        )
        rows.append(
            (
                "G4 recheck",
                "players within 10 m detected, release frame",
                f"{rel10:.4f}",
                f">= {G4_MIN_PLAYERS_DETECTED:.2f}",
                verdict(rel10 >= G4_MIN_PLAYERS_DETECTED),
            )
        )
        rows.append(
            (
                "G4 recheck",
                "players within 10 m detected, pickup frame",
                f"{pk10:.4f}",
                f">= {G4_MIN_PLAYERS_DETECTED:.2f}",
                verdict(pk10 >= G4_MIN_PLAYERS_DETECTED),
            )
        )
        rows.append(
            (
                "G4 recheck",
                "winner detected on pickup frame (radius-free)",
                f"{win:.4f}",
                f">= {G4_MIN_WINNER_DETECTED:.2f}",
                verdict(win >= G4_MIN_WINNER_DETECTED),
            )
        )
    rows.append(("G4", "verdict", "", "", verdict(g4_ok)))

    print("\nGate verdicts:\n")
    print(
        pd.DataFrame(rows, columns=["gate", "criterion", "value", "threshold", "result"]).to_markdown(
            index=False
        )
    )

    print("\nG3 by trigger class, main pairs:\n")
    t = []
    for trig in [*episodes.LOOSE_TRIGGERS, "all"]:
        d = main_set if trig == "all" else main_set[main_set["trigger"] == trig]
        if len(d):
            a, b = g3_values(d)
            t.append({"trigger": trig, "pairs": len(d), "ball detected share": a, "camera loss share": b})
    print(pd.DataFrame(t).to_markdown(index=False, floatfmt=".3f"))

    print("\nG4 by trigger class, main pairs:\n")
    t = []
    for trig in [*episodes.LOOSE_TRIGGERS, "all"]:
        d = main_set if trig == "all" else main_set[main_set["trigger"] == trig]
        if len(d):
            r15, p15, w = g4_values(d, 15)
            r10, p10, _ = g4_values(d, 10)
            t.append(
                {
                    "trigger": trig,
                    "pairs": len(d),
                    "release 15 m": r15,
                    "pickup 15 m": p15,
                    "release 10 m": r10,
                    "pickup 10 m": p10,
                    "winner detected": w,
                }
            )
    print(pd.DataFrame(t).to_markdown(index=False, floatfmt=".3f"))


if __name__ == "__main__":
    main()
