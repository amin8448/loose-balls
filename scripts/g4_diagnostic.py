"""Diagnostic after G4: release-frame detection by whether the pickup point is in the camera view.

Not a gate and not a recheck; no threshold applies. Camera view: the image_corners_projection
polygon of the release frame.
"""

import numpy as np
import pandas as pd
from matplotlib.path import Path

from looseball_research import episodes, tracking

CORNERS = ("top_left", "top_right", "bottom_right", "bottom_left")


def main() -> None:
    ep = episodes.all_episodes()
    main_set = ep[ep["main"]].copy()
    inside = pd.Series(False, index=main_set.index)
    for m, d in main_set.groupby("match_id"):
        fr = tracking.load_frames(m)
        for i, r in d.iterrows():
            row = fr.iloc[int(r["release_frame"])]
            poly = np.array(
                [
                    (row[f"image_corners_projection.x_{c}"], row[f"image_corners_projection.y_{c}"])
                    for c in CORNERS
                ]
            )
            if not np.isnan(poly).any():
                inside[i] = Path(poly).contains_point((r["pickup_x"], r["pickup_y"]))
    main_set["pickup_in_view_at_release"] = inside
    rows = []
    for label, mask in (
        ("inside", inside),
        ("outside or no camera view", ~inside),
        ("all", inside | ~inside),
    ):
        d = main_set[mask]
        for radius in (15, 10):
            n = d[[f"release_n{radius}_releasing", f"release_n{radius}_other"]].to_numpy().sum()
            k = d[[f"release_det{radius}_releasing", f"release_det{radius}_other"]].to_numpy().sum()
            rows.append(
                {
                    "pickup point at release": label,
                    "radius m": radius,
                    "pairs": len(d),
                    "players": int(n),
                    "detected share": k / n,
                }
            )
    print(pd.DataFrame(rows).to_markdown(index=False, floatfmt=".3f"))
    print()
    t = (
        main_set.groupby("trigger")["pickup_in_view_at_release"]
        .agg(pairs="size", inside="mean")
        .reset_index()
    )
    print(
        t.rename(columns={"inside": "share with pickup point in view at release"}).to_markdown(
            index=False, floatfmt=".3f"
        )
    )


if __name__ == "__main__":
    main()
