"""Coach versions of four hand-chosen animation candidates (AUDIT.md, "3h animation: coach versions").

Usage: python scripts/s3h_coach.py [OUT_DIR]   (default audit/animations_v2/coach, not committed)

Candidates 13, 2, 3 and 11 of the seed 20261119 set (audit/animations_v2/candidates/
candidate_seed20261119.csv), chosen by hand for a presentation, not drawn. Each is written at full
length (from the release) and as a short cut starting 2 s before the anchor, each with a contact
sheet.
"""

import sys
from pathlib import Path

import pandas as pd

from looseball.animate import animate

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "opendata"
CHOSEN = (13, 2, 3, 11)
SHORT_START = 2.0  # seconds before the anchor


def main(out_dir: str | None) -> None:
    out = Path(out_dir) if out_dir else ROOT / "audit" / "animations_v2" / "coach"
    out.mkdir(parents=True, exist_ok=True)
    cands = pd.read_csv(
        ROOT / "audit" / "animations_v2" / "candidates" / "candidate_seed20261119.csv"
    ).set_index("clip")
    rows = []
    for clip in CHOSEN:
        b = cands.loc[clip]
        for cut, start in (("full", None), ("short", SHORT_START)):
            stem = f"coach_candidate{clip:02d}_{b.verdict}_{b.enough_type}_{int(b.match_id)}_{int(b.seq_i)}_{cut}"
            info = animate(DATA, int(b.match_id), int(b.seq_i), out / f"{stem}.mp4", start_before_anchor=start,
                           sheet=out / f"{stem}_sheet.png")  # fmt: skip
            rows.append({"candidate": clip, "cut": cut, "match_id": int(b.match_id), "seq_i": int(b.seq_i),
                         "verdict": b.verdict, "enough_type": b.enough_type, "seconds": info["seconds"],
                         "label clearance px": info["label clearance px"], "file": Path(info["file"]).name})  # fmt: skip
    t = pd.DataFrame(rows)
    t.to_csv(out / "coach.csv", index=False, float_format="%.2f")
    print(t.to_markdown(index=False, floatfmt=".2f"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
