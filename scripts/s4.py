"""S4: camera gate (D7) and the immediate class on the anchored main pairs."""

import numpy as np
import pandas as pd
from step2_common import episode_table

from looseball import gate


def md(t: pd.DataFrame, floatfmt: str = ".3f") -> str:
    return t.to_markdown(index=False, floatfmt=floatfmt)


def main() -> None:
    t = episode_table()
    t["winner"] = np.where(t["releasing_won"] == 1, "releasing team", "other team")
    n = t["n_releasing"] + t["n_other"]
    k = t["n_detected_releasing"] + t["n_detected_other"]
    players_ok = (n == 0) | (k >= gate.GATE_SHARE * n)
    winner_ok = t["winner_detected_pickup"].astype(bool)
    print(f"anchored main pairs: {len(t)}\n")

    print("S4a. D7 drop rates by trigger:\n")
    print(md(gate.drop_rates(t, "trigger")))
    print("\nS4b. D7 drop rates by winner:\n")
    print(md(gate.drop_rates(t, "winner")))
    print("\nS4c. Reason for dropping:\n")
    reasons = pd.DataFrame(
        [
            {"reason": "under 85% of players within 15 m detected at the anchor only", "episodes": int((~players_ok & winner_ok).sum())},
            {"reason": "winner not detected at pickup only", "episodes": int((players_ok & ~winner_ok).sum())},
            {"reason": "both", "episodes": int((~players_ok & ~winner_ok).sum())},
            {"reason": "kept", "episodes": int((players_ok & winner_ok).sum())},
        ]
    )  # fmt: skip
    print(md(reasons, ".0f"))
    w = gate.win_share_difference(t, n_boot=2000, seed=0)
    print(
        "\nS4d. Releasing team's win share, dropped against kept (interval: 2000 bootstrap replicates within match, seed 0):\n"
    )
    print(md(pd.DataFrame([w])))

    for title, d in (("all anchored main pairs", t), ("pairs kept by D7", t[t["kept"]])):
        for by in ("trigger", "winner"):
            g = d.groupby(by)["immediate"].agg(episodes="size", immediate="sum", share="mean").reset_index()
            g = pd.concat([g, pd.DataFrame([{by: "all", "episodes": len(d), "immediate": int(d["immediate"].sum()),
                                             "share": d["immediate"].mean()}])], ignore_index=True)  # fmt: skip
            print(f"\nS4e. Immediate class (lead < 0.5 s) by {by}, {title}:\n")
            print(md(g))


if __name__ == "__main__":
    main()
