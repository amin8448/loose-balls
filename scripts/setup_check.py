"""Setup check: frame counts by frame class and player_possession rows per exploration match."""

import pandas as pd

from looseball_research import io, paths, tracking

rows = []
for m in paths.EXPLORATION:
    fr = tracking.load_frames(m)
    ev = io.load_events(m)
    in_period = fr["period"].notna()
    counts = fr.loc[in_period, "frame_class"].value_counts()
    assert (fr["frame"].to_numpy() == range(len(fr))).all(), "frame numbers are not contiguous"
    rows.append(
        {
            "match": m,
            "frames": len(fr),
            "outside periods": int((~in_period).sum()),
            "in periods": int(in_period.sum()),
            "camera": int(counts.get("camera", 0)),
            "no camera": int(counts.get("no_camera", 0)),
            "empty": int(counts.get("empty", 0)),
            "camera share": counts.get("camera", 0) / in_period.sum(),
            "player_possession rows": int((ev["event_type"] == "player_possession").sum()),
        }
    )
t = pd.DataFrame(rows)
total = t.drop(columns=["match", "camera share"]).sum().to_dict()
total["camera share"] = total["camera"] / total["in periods"]
t = pd.concat([t.astype({"match": str}), pd.DataFrame([{"match": "total", **total}])], ignore_index=True)
t["camera share"] = t["camera share"].map(lambda v: f"{v:.3f}")
print(t.to_markdown(index=False))
